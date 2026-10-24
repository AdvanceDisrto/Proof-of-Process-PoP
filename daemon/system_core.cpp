#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <fcntl.h>
#include <functional>
#include <iostream>
#include <mutex>
#include <netinet/in.h>
#include <queue>
#include <string>
#include <sys/socket.h>
#include <thread>
#include <unordered_map>
#include <unistd.h>
#include <vector>
#if defined(__AVX2__)
#include <immintrin.h>
#elif defined(__ARM_NEON) || defined(__aarch64__)
#include <arm_neon.h>
#endif

struct SessionState { uint64_t last_nonce; std::chrono::steady_clock::time_point last_active; };
class SessionManager {
    std::unordered_map<std::string, SessionState> sessions;
    std::mutex mutex;
public:
    bool validate_and_update(const std::string& id, uint64_t nonce) {
        std::lock_guard<std::mutex> lock(mutex);
        const auto now = std::chrono::steady_clock::now();
        const auto it = sessions.find(id);
        if (it != sessions.end()) {
            if (nonce <= it->second.last_nonce) return false;
            it->second = {nonce, now};
            return true;
        }
        sessions.emplace(id, SessionState{nonce, now});
        return true;
    }
};

struct EnergySample { bool available = false; uint64_t microjoules = 0; };
class HardwareTelemetry {
    static EnergySample read_path(const char* path) {
        const int fd = open(path, O_RDONLY);
        if (fd < 0) return {};
        std::array<char, 64> buffer{};
        const ssize_t count = read(fd, buffer.data(), buffer.size() - 1);
        close(fd);
        if (count <= 0) return {};
        uint64_t value = 0;
        const auto parsed = std::from_chars(buffer.data(), buffer.data() + count, value);
        if (parsed.ec != std::errc()) return {};
        return {true, value};
    }
public:
    static EnergySample read_rapl() {
        return read_path("/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj");
    }
    static bool tpm_node_present() {
        return access("/dev/tpmrm0", F_OK) == 0 || access("/dev/tpm0", F_OK) == 0;
    }
};

class SIMDProcessor {
public:
    static const char* backend() {
#if defined(__AVX2__)
        return "AVX2";
#elif defined(__ARM_NEON) || defined(__aarch64__)
        return "NEON";
#else
        return "SCALAR";
#endif
    }
    static void process(const uint8_t* input, uint8_t* output, size_t length) {
        size_t index = 0;
#if defined(__AVX2__)
        const __m256i mask = _mm256_set1_epi8(static_cast<char>(0xAA));
        for (; index + 32 <= length; index += 32) {
            auto value = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(input + index));
            value = _mm256_xor_si256(value, mask);
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(output + index), value);
        }
#elif defined(__ARM_NEON) || defined(__aarch64__)
        const uint8x16_t mask = vdupq_n_u8(0xAA);
        for (; index + 16 <= length; index += 16) {
            auto value = vld1q_u8(input + index);
            value = veorq_u8(value, mask);
            vst1q_u8(output + index, value);
        }
#endif
        for (; index < length; ++index) output[index] = input[index] ^ 0xAA;
    }
};

class ThreadPool {
    std::vector<std::thread> workers;
    std::queue<std::function<void()>> tasks;
    std::mutex mutex;
    std::condition_variable condition;
    bool stop = false;
public:
    explicit ThreadPool(size_t count) {
        count = std::max<size_t>(1, count);
        for (size_t i = 0; i < count; ++i) {
            workers.emplace_back([this] {
                for (;;) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(mutex);
                        condition.wait(lock, [this] { return stop || !tasks.empty(); });
                        if (stop && tasks.empty()) return;
                        task = std::move(tasks.front());
                        tasks.pop();
                    }
                    task();
                }
            });
        }
    }
    template<class F> void enqueue(F&& task) {
        {
            std::lock_guard<std::mutex> lock(mutex);
            tasks.emplace(std::forward<F>(task));
        }
        condition.notify_one();
    }
    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lock(mutex);
            stop = true;
        }
        condition.notify_all();
        for (auto& worker : workers) worker.join();
    }
};

static SessionManager sessions;

static void send_all(int fd, const std::string& data) {
    size_t offset = 0;
    while (offset < data.size()) {
        const ssize_t sent = send(fd, data.data() + offset, data.size() - offset, 0);
        if (sent <= 0) break;
        offset += static_cast<size_t>(sent);
    }
}

static void handle_client(int fd) {
    std::array<char, 2048> buffer{};
    const ssize_t count = read(fd, buffer.data(), buffer.size() - 1);
    if (count <= 0) { close(fd); return; }

    const uint64_t nonce = static_cast<uint64_t>(
        std::chrono::steady_clock::now().time_since_epoch().count());
    if (!sessions.validate_and_update("CLIENT_ALPHA", nonce)) {
        send_all(fd, "HTTP/1.1 409 Conflict\r\nContent-Length: 6\r\n\r\nreplay");
        close(fd);
        return;
    }

    const auto start = HardwareTelemetry::read_rapl();
    const bool tpm_present = HardwareTelemetry::tpm_node_present();
    std::vector<uint8_t> input(1U << 20, 0x55);
    std::vector<uint8_t> output(input.size());
    SIMDProcessor::process(input.data(), output.data(), input.size());
    const auto end = HardwareTelemetry::read_rapl();

    const bool energy_observed =
        start.available && end.available && end.microjoules >= start.microjoules;
    const uint64_t delta = energy_observed ? end.microjoules - start.microjoules : 0;

    std::string body =
        "{\"state\":\"VERIFIED_PROCESS\",\"physical_gate\":\"ACTION_REQUIRED\","
        "\"simd_backend\":\"" + std::string(SIMDProcessor::backend()) + "\","
        "\"rapl_observed\":" + (energy_observed ? std::string("true") : std::string("false")) + ","
        "\"energy_delta_uj\":" + (energy_observed ? std::to_string(delta) : std::string("null")) + ","
        "\"tpm_device_present\":" + (tpm_present ? std::string("true") : std::string("false")) + ","
        "\"does_not_prove\":[\"TPM quote or hardware-rooted attestation\","
        "\"RAPL calibration or workload-exclusive energy attribution\","
        "\"fabricated custom silicon or foundry signoff\"]}";

    const std::string headers =
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " +
        std::to_string(body.size()) + "\r\nConnection: close\r\n\r\n";
    send_all(fd, headers + body);
    close(fd);
}

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--self-test") {
        std::vector<uint8_t> input(97, 0x55);
        std::vector<uint8_t> output(input.size());
        SIMDProcessor::process(input.data(), output.data(), input.size());
        if (!std::all_of(output.begin(), output.end(), [](uint8_t value) { return value == 0xFF; })) return 2;
        SessionManager manager;
        if (!manager.validate_and_update("x", 1)) return 3;
        if (manager.validate_and_update("x", 1)) return 4;
        if (!manager.validate_and_update("x", 2)) return 5;
        std::cout << "daemon self-test: PASS backend=" << SIMDProcessor::backend() << "\n";
        return 0;
    }

    const int server = socket(AF_INET, SOCK_STREAM, 0);
    if (server < 0) return 1;
    int option = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &option, sizeof(option));
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(8080);
    if (bind(server, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) {
        perror("bind");
        close(server);
        return 1;
    }
    if (listen(server, SOMAXCONN) < 0) {
        close(server);
        return 1;
    }
    ThreadPool pool(std::thread::hardware_concurrency());
    std::cout << "iBare daemon listening 8080 SIMD=" << SIMDProcessor::backend() << "\n";
    for (;;) {
        const int fd = accept(server, nullptr, nullptr);
        if (fd >= 0) pool.enqueue([fd] { handle_client(fd); });
    }
}

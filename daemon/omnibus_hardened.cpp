#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include <openssl/evp.h>

#if defined(__AVX2__)
#include <immintrin.h>
#elif defined(__ARM_NEON) || defined(__aarch64__)
#include <arm_neon.h>
#endif

namespace {
using PKey = std::unique_ptr<EVP_PKEY, decltype(&EVP_PKEY_free)>;
using MdCtx = std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)>;

const char* simd_backend() {
#if defined(__AVX2__)
    return "AVX2";
#elif defined(__ARM_NEON) || defined(__aarch64__)
    return "NEON";
#else
    return "SCALAR";
#endif
}

void vector_xor(const uint8_t* source, uint8_t* dest, size_t length) {
    size_t i = 0;
#if defined(__AVX2__)
    const __m256i mask = _mm256_set1_epi8(0x5F);
    for (; i + 32 <= length; i += 32) {
        const __m256i data = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(source + i));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(dest + i), _mm256_xor_si256(data, mask));
    }
#elif defined(__ARM_NEON) || defined(__aarch64__)
    const uint8x16_t mask = vdupq_n_u8(0x5F);
    for (; i + 16 <= length; i += 16) {
        const uint8x16_t data = vld1q_u8(source + i);
        vst1q_u8(dest + i, veorq_u8(data, mask));
    }
#endif
    for (; i < length; ++i) dest[i] = source[i] ^ 0x5F;
}

PKey generate_key() {
    EVP_PKEY_CTX* raw = EVP_PKEY_CTX_new_id(EVP_PKEY_ED25519, nullptr);
    if (!raw) return {nullptr, EVP_PKEY_free};
    std::unique_ptr<EVP_PKEY_CTX, decltype(&EVP_PKEY_CTX_free)> ctx(raw, EVP_PKEY_CTX_free);
    if (EVP_PKEY_keygen_init(ctx.get()) <= 0) return {nullptr, EVP_PKEY_free};
    EVP_PKEY* key = nullptr;
    if (EVP_PKEY_keygen(ctx.get(), &key) <= 0) return {nullptr, EVP_PKEY_free};
    return {key, EVP_PKEY_free};
}

std::vector<uint8_t> sign(EVP_PKEY* key, const std::string& payload) {
    MdCtx ctx(EVP_MD_CTX_new(), EVP_MD_CTX_free);
    if (!ctx || EVP_DigestSignInit(ctx.get(), nullptr, nullptr, nullptr, key) <= 0) return {};
    size_t size = 0;
    if (EVP_DigestSign(ctx.get(), nullptr, &size,
        reinterpret_cast<const unsigned char*>(payload.data()), payload.size()) <= 0) return {};
    std::vector<uint8_t> signature(size);
    if (EVP_DigestSign(ctx.get(), signature.data(), &size,
        reinterpret_cast<const unsigned char*>(payload.data()), payload.size()) <= 0) return {};
    signature.resize(size);
    return signature;
}

bool verify(EVP_PKEY* key, const std::string& payload, const std::vector<uint8_t>& signature) {
    MdCtx ctx(EVP_MD_CTX_new(), EVP_MD_CTX_free);
    if (!ctx || EVP_DigestVerifyInit(ctx.get(), nullptr, nullptr, nullptr, key) <= 0) return false;
    return EVP_DigestVerify(ctx.get(), signature.data(), signature.size(),
        reinterpret_cast<const unsigned char*>(payload.data()), payload.size()) == 1;
}

std::string hex(const std::vector<uint8_t>& bytes) {
    std::ostringstream out;
    for (uint8_t byte : bytes) out << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(byte);
    return out.str();
}
}  // namespace

int main() {
    std::array<uint8_t, 256> input{};
    std::array<uint8_t, 256> output{};
    input.fill(0xA5);
    vector_xor(input.data(), output.data(), output.size());
    for (uint8_t byte : output) if (byte != 0xFA) return 2;

    auto key = generate_key();
    if (!key) return 3;
    const std::string payload =
        "{\"state\":\"VERIFIED_PROCESS\",\"physical_gate\":\"ACTION_REQUIRED\","
        "\"simd_backend\":\"" + std::string(simd_backend()) + "\","
        "\"key_provenance\":\"EPHEMERAL_OPENSSL_SOFTWARE_KEY\","
        "\"does_not_prove\":[\"A19 Pro execution\",\"Secure Enclave key custody\","
        "\"physical energy measurement\",\"device attestation\"]}";
    const auto signature = sign(key.get(), payload);
    if (signature.size() != 64 || !verify(key.get(), payload, signature)) return 4;
    std::string tampered = payload;
    tampered.push_back(' ');
    if (verify(key.get(), tampered, signature)) return 5;

    std::cout << payload << "\n";
    std::cout << "ed25519_signature=" << hex(signature) << "\n";
    std::cout << "hardened self-test: PASS backend=" << simd_backend() << "\n";
    return 0;
}

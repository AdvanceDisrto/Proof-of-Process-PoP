// STRMKRD Rev0 Linux I2C observation tool — not a secure-element signer.
// Uses real /dev/i2c-N character devices, with I2C_RDWR combined transactions.
// ATECC608C does NOT expose arbitrary addressable serial-number registers.
// Its serial/Sign/GenKey operations require the official CryptoAuthLib protocol.
// NEVER accept this software as evidence of FIPS certification or silicon signing.
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <numeric>
#include <stdexcept>
#include <string>
#include <sys/ioctl.h>
#include <unistd.h>
#include <vector>

namespace strmkrd {
constexpr uint8_t MCP_ADDR = 0x18;
constexpr uint8_t INA_ADDR = 0x40;
constexpr int MIN_TEMP_SIXTEENTHS = -640;
constexpr int MAX_TEMP_SIXTEENTHS = 2000;

uint16_t decode_be16(const uint8_t* data) {
    if (!data) throw std::invalid_argument("null register bytes");
    return static_cast<uint16_t>((data[0] << 8) | data[1]);
}
int mcp_temperature_sixteenths(uint16_t reg) {
    int value = static_cast<int>(reg & 0x1fff);
    if (value & 0x1000) value -= 0x2000;
    if (value < MIN_TEMP_SIXTEENTHS || value > MAX_TEMP_SIXTEENTHS)
        throw std::runtime_error("temperature outside MCP9808 specified range");
    return value;
}
int signed16(uint16_t word) {
    return word >= 32768 ? static_cast<int>(word) - 65536 : static_cast<int>(word);
}
uint16_t ina_calibration(uint32_t shunt_uohm = 2000, uint32_t current_lsb_microamp = 1000) {
    if (!shunt_uohm || !current_lsb_microamp) throw std::invalid_argument("zero calibration input");
    // CAL = 0.00512 / (R_shunt[ohm] * I_LSB[A]); integer-micro unit rearrangement.
    const uint64_t numerator = UINT64_C(5120000000);
    const uint64_t denominator = static_cast<uint64_t>(shunt_uohm) * current_lsb_microamp;
    if (numerator % denominator != 0) throw std::invalid_argument("noninteger calibration");
    const uint64_t result = numerator / denominator;
    if (result < 1 || result > 65535) throw std::invalid_argument("INA226 calibration overflow");
    return static_cast<uint16_t>(result);
}
class MedianWindow {
    std::vector<int> samples_;
    static constexpr size_t LIMIT = 7;
public:
    int push(int sample) {
        // Raw sample must be checked first: a median may conceal a dangerous excursion.
        if (sample < MIN_TEMP_SIXTEENTHS || sample > MAX_TEMP_SIXTEENTHS)
            throw std::invalid_argument("raw reading invalid");
        if (samples_.size() == LIMIT) samples_.erase(samples_.begin());
        samples_.push_back(sample);
        auto tmp = samples_;
        std::sort(tmp.begin(), tmp.end());
        return tmp[tmp.size()/2];
    }
};
class LinuxI2C {
    int fd_ = -1;
public:
    explicit LinuxI2C(const std::string& device) {
        if (device.rfind("/dev/i2c-", 0) != 0) throw std::invalid_argument("not an I2C device path");
        fd_ = ::open(device.c_str(), O_RDWR | O_CLOEXEC);
        if (fd_ < 0) throw std::runtime_error("I2C open failed: " + std::string(std::strerror(errno)));
    }
    ~LinuxI2C(){ if (fd_ >= 0) ::close(fd_); }
    LinuxI2C(const LinuxI2C&) = delete;
    LinuxI2C& operator=(const LinuxI2C&) = delete;
    uint16_t read16(uint8_t addr, uint8_t reg) {
        uint8_t regbuf = reg, bytes[2] = {0,0};
        struct i2c_msg msg[2] = {};
        msg[0].addr = addr; msg[0].flags = 0; msg[0].len = 1; msg[0].buf = &regbuf;
        msg[1].addr = addr; msg[1].flags = I2C_M_RD; msg[1].len = 2; msg[1].buf = bytes;
        struct i2c_rdwr_ioctl_data transfer = {msg,2};
        if (::ioctl(fd_, I2C_RDWR, &transfer) < 0)
            throw std::runtime_error("I2C_RDWR failed: " + std::string(std::strerror(errno)));
        return decode_be16(bytes);
    }
};

void self_test() {
    const uint8_t bytes[] = {0x01,0x88};
    if (decode_be16(bytes)!=0x0188) throw std::runtime_error("byte order incorrect");
    if (mcp_temperature_sixteenths(0x0188)!=392) throw std::runtime_error("positive temperature failed");
    if (mcp_temperature_sixteenths(0x1ff0)!=-16) throw std::runtime_error("negative temperature failed");
    if (mcp_temperature_sixteenths(0xe188)!=392) throw std::runtime_error("alert bits not masked");
    if (signed16(0xffff)!=-1) throw std::runtime_error("negative INA226 current failed");
    if (ina_calibration()!=2560) throw std::runtime_error("INA226 scaling failed");
    MedianWindow window;
    for (auto v: {960,960,960,0,960,960,960})
        if(window.push(v)!=960)throw std::runtime_error("median window false reject");
    bool rejected=false;
    try{ window.push(32767); }catch(const std::invalid_argument&){ rejected=true; }
    if(!rejected)throw std::runtime_error("invalid raw sensor wasn't rejected");
    std::cout << R"({"status":"PASS","tier":"REGISTER_VECTORS_ONLY","physical_hardware":"NOT_VERIFIED","hardware_signature":"NOT_VERIFIED"})" << '\n';
}
void hardware_cycle(const std::string& dev) {
    LinuxI2C bus(dev);
    if (bus.read16(MCP_ADDR,0x06)!=0x0054) throw std::runtime_error("MCP9808 manufacturer mismatch");
    if (bus.read16(INA_ADDR,0xfe)!=0x5449) throw std::runtime_error("INA226 manufacturer mismatch");
    const auto temp = mcp_temperature_sixteenths(bus.read16(MCP_ADDR,0x05));
    // Calibration is expected to have been set only through a separately reviewed,
    // explicit authorized step. Never overwrite calibration during a read-only probe.
    if (bus.read16(INA_ADDR,0x05)!=ina_calibration())
        throw std::runtime_error("INA226 calibration unconfigured/mismatch");
    const uint16_t volt = bus.read16(INA_ADDR,0x02);
    const int curr = signed16(bus.read16(INA_ADDR,0x04));
    const uint16_t power = bus.read16(INA_ADDR,0x03);
    if (volt>28800)throw std::runtime_error("INA226 voltage out of specified range");
    // 1.25mV/tick; 25*Current_LSB(A) mW/tick for 1mA current LSB.
    std::cout << R"({"spec":"strmkrd/rev0/native-i2c/v1","tier":"UNAUTHENTICATED_I2C_OBSERVATION",)"
              << "\"temperature_sixteenths_c\":" << temp
              << ",\"ina_bus_ticks\":" << volt
              << ",\"ina_current_ticks\":" << curr
              << ",\"ina_power_ticks\":" << power
              << R"(,"hardware_signature":"NOT_PRESENT","calibration_traceability":"NOT_VERIFIED"})"
              << '\n';
}
}
int main(int argc,char** argv){
    try {
        if (argc==2 && std::string(argv[1])=="--self-test"){
            strmkrd::self_test();
            return 0;
        }
        if (argc==3 && std::string(argv[1])=="--hardware"){
            strmkrd::hardware_cycle(argv[2]);
            return 0;
        }
        std::cerr << "usage: strmkrd-i2c-driver --self-test | --hardware /dev/i2c-1\n";
        return 64;
    }catch(const std::exception& e){
        std::cerr << "HARDWARE_GATE_FAILED (" << e.what() << "); no signed receipt minted\n";
        return 2;
    }
}

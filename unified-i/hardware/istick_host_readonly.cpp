// iNNOVULIS iStick host-side safety gate; no USB, I2C, OTP, lock or firmware flash.
// This does not run on the RP2040; hardware firmware is a separate build gate.
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

struct DeviceStatus {
  bool sensor_present;
  bool signer_present;
  bool operator_approved;
  bool witness_verified;
};

bool may_request_hardware_sign(const DeviceStatus &d) noexcept {
  // A signature request does NOT prove the MCU/sensor is genuine.
  return d.sensor_present && d.signer_present && d.operator_approved && d.witness_verified;
}

int main(int argc, char **argv) {
  if (argc != 2 || std::string(argv[1]) != "--self-test") {
    std::cerr << "This executable is host-side test logic only. No devices are accessed.\n";
    return 64;
  }
  for (int bits = 0; bits < 16; ++bits) {
    DeviceStatus state{bool(bits & 1), bool(bits & 2), bool(bits & 4), bool(bits & 8)};
    const bool want = bits == 15;
    if (may_request_hardware_sign(state) != want) {
      std::cerr << "FAIL gate vector " << bits << "\n";
      return 1;
    }
  }
  std::cout << "ISTICK_CPP_HOST_GATE=PASS vectors=16; PHYSICAL_SIGNING=NOT_ATTEMPTED\n";
  return 0;
}

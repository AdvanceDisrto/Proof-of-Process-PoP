"""Read-only MCP9808 identity+telemetry; host values are not authenticated physics.

No writes, EEPROM locks, fuses, proprietary provisioning or device claiming.
"""
from __future__ import annotations
from dataclasses import dataclass
import time

class SensorUnavailable(RuntimeError):pass

@dataclass(frozen=True)
class TemperatureSample:
    device: str
    address: str
    temperature_milli_celsius: int
    source_tier: str
    clock: str
    calibration: str
    proof_of_real_world_accuracy: bool = False

class MCP9808ReadOnly:
    def __init__(self, bus, *, address=0x18):
        if type(address) is not int or address not in range(0x18,0x20):
            raise ValueError("MCP9808 I2C address 0x18–0x1f only")
        self.bus=bus;self.address=address

    def _reg(self, reg):
        try:
            # smbus2 reports SMBus read_word_data in opposite byte order
            raw=self.bus.read_word_data(self.address,reg)
            if type(raw) is not int or not 0 <= raw <= 65535:
                raise SensorUnavailable("invalid register word")
            return ((raw&255)<<8)|(raw>>8)
        except (OSError,AttributeError) as exc:
            raise SensorUnavailable("I2C bus read unavailable") from exc

    def read(self):
        if self._reg(0x06)!=0x0054:raise SensorUnavailable("MCP9808 manufacturer ID mismatch")
        if (self._reg(0x07)&0xFF00)!=0x0400:raise SensorUnavailable("MCP9808 device ID mismatch")
        raw=self._reg(0x05)
        frac=(raw&0x0fff) * 625 # 0.0625 C increments / convert from units of 1/16C to 1/10000C
        milli=frac//10
        if raw&0x1000:milli-=256000
        if not -40000<=milli<=125000:
            raise SensorUnavailable("sensor sample outside rated interval")
        return TemperatureSample("MCP9808",f"0x{self.address:02x}",milli,
                                 "HARDWARE_UNATTESTED","HOST_MONOTONIC_UNTRUSTED",
                                 "NOT_INDEPENDENTLY_CALIBRATED")

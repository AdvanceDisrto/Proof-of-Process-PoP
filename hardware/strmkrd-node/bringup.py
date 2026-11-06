"""STRMKRD REV0 Linux I2C hardware bring-up.

This is an actual read-only sensor probe, not a hardware attestation.
It intentionally does not sign hardware evidence or call QoW/PoP when no
provisioned secure element or trusted sensor bus is available.

Command:
  python hardware/strmkrd-node/bringup.py --self-test
  python hardware/strmkrd-node/bringup.py --hardware --bus 1 --ina-address 0x40

The optional INA226 register write requires explicit --calibrate-ina.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
import json
import sys
import time
from typing import Protocol


class ReadWordBus(Protocol):
    def read_i2c_block_data(self, address: int, register: int, count: int) -> list[int]: ...
    def write_i2c_block_data(self, address: int, register: int, data: list[int]) -> None: ...


def read_be16(bus: ReadWordBus, address: int, register: int) -> int:
    data = bus.read_i2c_block_data(address, register, 2)
    if len(data) != 2 or any(type(v) is not int or v < 0 or v > 255 for v in data):
        raise ValueError("incomplete I2C register read")
    return (data[0] << 8) | data[1]


def write_be16(bus: ReadWordBus, address: int, register: int, value: int) -> None:
    if type(value) is not int or not (0 <= value <= 0xFFFF):
        raise ValueError("invalid 16-bit register")
    bus.write_i2c_block_data(address, register, [value >> 8, value & 0xFF])


def read_mcp9808(bus: ReadWordBus, address: int = 0x18) -> dict:
    """Ambient temperature register 0x05, 1/16 °C exact fixed-point decoding."""
    raw = read_be16(bus, address, 0x05)
    # Bits 15:13 are alert flags. 12 is sign bit, 11:0 is magnitude.
    count = raw & 0x1FFF
    if count & 0x1000:
        count -= 0x2000
    temp_c = Decimal(count) / Decimal(16)
    if not (Decimal("-40") <= temp_c <= Decimal("125")):
        raise ValueError("MCP9808 observation outside nominal sensor range")
    return {
        "part": "MCP9808", "i2c_address": hex(address),
        "raw_register_0x05": f"0x{raw:04x}",
        "temperature_sixteenths_c": count,
        "temperature_c": str(temp_c),
        "source_tier": "UNAUTHENTICATED_I2C_OBSERVATION",
    }


@dataclass(frozen=True)
class Ina226Config:
    address: int = 0x40
    shunt_ohms: Decimal = Decimal("0.002")
    current_lsb_amps: Decimal = Decimal("0.001")

    def calibration(self) -> int:
        if self.shunt_ohms <= 0 or self.current_lsb_amps <= 0:
            raise ValueError("shunt and current LSB must be positive")
        cal = Decimal("0.00512") / (self.shunt_ohms * self.current_lsb_amps)
        if cal != cal.to_integral_value() or not (1 <= int(cal) <= 65535):
            raise ValueError("unsupported INA226 calibration scaling")
        return int(cal)


def read_ina226(bus: ReadWordBus, cfg: Ina226Config, *, initialize: bool = False) -> dict:
    """Reads TI INA226 registers; power is in W, NOT joules."""
    expected = cfg.calibration()
    maker = read_be16(bus, cfg.address, 0xFE)
    if maker != 0x5449:
        raise ValueError(f"unexpected INA226 manufacturer ID 0x{maker:04x}")
    if initialize:
        write_be16(bus, cfg.address, 0x05, expected)
    installed = read_be16(bus, cfg.address, 0x05)
    if installed != expected:
        raise ValueError(f"INA226 calibration mismatch: {installed} != {expected}")
    voltage_raw = read_be16(bus, cfg.address, 0x02)
    current_raw = read_be16(bus, cfg.address, 0x04)
    power_raw = read_be16(bus, cfg.address, 0x03)
    signed_current = current_raw if current_raw < 0x8000 else current_raw - 0x10000
    bus_v = Decimal(voltage_raw) * Decimal("0.00125")
    current_a = Decimal(signed_current) * cfg.current_lsb_amps
    power_w = Decimal(power_raw) * Decimal(25) * cfg.current_lsb_amps
    if bus_v > Decimal("36"):
        raise ValueError("INA226 bus voltage above specified common-mode range")
    return {
        "part": "INA226", "i2c_address": hex(cfg.address),
        "manufacturer_id": f"0x{maker:04x}",
        "bus_v": str(bus_v), "current_a": str(current_a), "power_w": str(power_w),
        "calibration_register": installed,
        "current_lsb_a": str(cfg.current_lsb_amps), "shunt_ohms": str(cfg.shunt_ohms),
        "source_tier": "UNAUTHENTICATED_I2C_OBSERVATION",
    }


class EnergyIntegrator:
    """Integrates sample power over *monotonic* time; no physical accuracy claim."""
    def __init__(self, max_gap_seconds: Decimal = Decimal("5")):
        self.previous: tuple[Decimal, Decimal] | None = None
        self.joules = Decimal(0)
        self.max_gap_seconds = max_gap_seconds
        self.intervals = 0

    def observe(self, elapsed_seconds: Decimal, watts: Decimal) -> Decimal:
        if not elapsed_seconds.is_finite() or not watts.is_finite() or watts < 0:
            raise ValueError("invalid monotonic timestamp or power sample")
        if self.previous is not None:
            prev_time, prev_watts = self.previous
            delta = elapsed_seconds - prev_time
            if delta <= 0 or delta > self.max_gap_seconds:
                raise ValueError("energy integration gap or timestamp regression")
            self.joules += (prev_watts + watts) * delta / Decimal(2)
            self.intervals += 1
        self.previous = elapsed_seconds, watts
        return self.joules


def build_unsigned_observation(temp: dict, power: dict, monotonic_ns: int) -> dict:
    if temp["source_tier"] != "UNAUTHENTICATED_I2C_OBSERVATION" or power["source_tier"] != "UNAUTHENTICATED_I2C_OBSERVATION":
        raise ValueError("invalid source tier")
    return {
        "spec": "strmkrd/rev0/raw-sensor-observation/v1",
        "source_tier": "UNAUTHENTICATED_I2C_OBSERVATION",
        "physical_device_authentication": "NOT_VERIFIED",
        "silicon_signature": "NOT_PRESENT",
        "trusted_timestamp": False,
        "monotonic_ns": monotonic_ns,
        "temperature": temp,
        "power_meter": power,
        "does_not_prove": [
            "hardware secure key possession",
            "independently calibrated measurements",
            "physical origin of a cryptographic signature",
            "absolute energy consumed by a computation",
            "truth of a policy premise or physical safety",
        ],
    }


def hardware_probe(bus_id: int, ina_address: int, initialize: bool) -> dict:
    try:
        from smbus2 import SMBus  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install smbus2 on the physical Linux host") from exc
    with SMBus(bus_id) as bus:
        temperature = read_mcp9808(bus)
        power = read_ina226(bus, Ina226Config(address=ina_address), initialize=initialize)
    return build_unsigned_observation(temperature, power, time.monotonic_ns())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--hardware", action="store_true", help="read a real I2C bus; fail if absent")
    modes.add_argument("--self-test", action="store_true", help="run deterministic register decoding test vectors")
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--ina-address", type=lambda s: int(s, 0), default=0x40)
    parser.add_argument("--calibrate-ina", action="store_true", help="explicitly WRITE the INA226 calibration register")
    args = parser.parse_args()
    if args.self_test:
        if args.calibrate_ina:
            parser.error("--calibrate-ina only valid with --hardware")
        vectors = {
            "mcp9808_24_5": (0x0190, "25"),  # actual 0x0190 corresponds to 25 °C
            "mcp9808_negative": (0x1FF0, "-1"),
        }
        for name, (raw, expected) in vectors.items():
            class Fake:
                def read_i2c_block_data(self, _a, _r, _n): return [raw >> 8, raw & 255]
            actual = Decimal(read_mcp9808(Fake())["temperature_c"])
            if actual != Decimal(expected):
                raise AssertionError(f"{name}: {actual} != {expected}")
        print(json.dumps({"status": "PASS","tier": "DETERMINISTIC_I2C_TEST_VECTORS","real_hardware": "NOT_VERIFIED"}))
        return 0
    if args.bus < 0 or not (0x03 <= args.ina_address <= 0x77):
        parser.error("invalid I2C bus/address")
    try:
        observation = hardware_probe(args.bus, args.ina_address, args.calibrate_ina)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "HARDWARE_GATE_FAILED", "error_type": type(exc).__name__,
                          "real_hardware": "NOT_VERIFIED"}), file=sys.stderr)
        return 2
    print(json.dumps(observation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

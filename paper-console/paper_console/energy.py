"""INA226-ready bounded physical integration; no sampled values invented."""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PowerSample:
    monotonic_seconds: float
    watts: float
    volts: float
    amps: float
    device_id: str
    source: str
    calibration_id: str

    def __post_init__(self):
        if not self.device_id or not self.calibration_id or self.source != "INA226_UNATTESTED":
            raise ValueError("real meter and calibration identifiers required")
        for name in ("monotonic_seconds", "watts", "volts", "amps"):
            v=getattr(self, name)
            if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
                raise ValueError("negative/nonfinite or simulated meter sample")


class JouleIntegrator:
    """Trapezoidal numerical power integration, honest about sampling uncertainty."""
    def __init__(self, *, max_gap_seconds: float = 10.0):
        self.prev = None
        self.joules = 0.0
        self.segments = 0
        self.max_gap_seconds = max_gap_seconds

    def add(self, sample: PowerSample) -> float:
        if self.prev is not None:
            if (sample.device_id != self.prev.device_id or
                sample.calibration_id != self.prev.calibration_id):
                raise ValueError("cannot integrate different meter/calibration")
            dt = sample.monotonic_seconds - self.prev.monotonic_seconds
            if dt <= 0 or dt > self.max_gap_seconds:
                raise ValueError("nonmonotonic timestamp or sampling gap too wide")
            self.joules += 0.5 * dt * (sample.watts + self.prev.watts)
            self.segments += 1
        self.prev = sample
        return self.joules

    def receipt(self):
        if not self.segments:
            raise ValueError("at least two calibrated readings are required")
        return {"joules_estimate": round(self.joules, 9),
                "samples_integrated_segments": self.segments,
                "device_id": self.prev.device_id,
                "calibration_id": self.prev.calibration_id,
                "source": "INA226_UNATTESTED",
                "claims_not_established": ["hardware authenticity", "calibration by independent lab", "proof of computation"]}


class INA226:
    """Raw bus-voltage and shunt-voltage readout; requires smbus2, I2C, shunt calibration.

    INA226 register 0x01: signed shunt, 2.5 microvolts per LSB.
    INA226 register 0x02: bus voltage, 1.25 millivolts per LSB.
    Power estimate = busV * (shuntV / resistorOhms); not a direct Joules register.
    """
    def __init__(self, *, bus_number: int, address: int, shunt_ohms: float,
                 calibration_id: str, device_id: str, bus=None):
        if type(bus_number) is not int or bus_number < 0 or type(address) is not int or not 0x40 <= address <= 0x4f:
            raise ValueError("INA226 I2C address must be 0x40–0x4f")
        if not isinstance(shunt_ohms, (float, int)) or not 0 < shunt_ohms <= 1:
            raise ValueError("specific positive shunt value is required")
        if not calibration_id or not device_id:
            raise ValueError("specific calibration and device identity required")
        if bus is None:
            try:
                from smbus2 import SMBus
            except ImportError as exc:
                raise RuntimeError("smbus2 dependency and real I2C device are required") from exc
            bus=SMBus(bus_number)
        self.bus=bus;self.address=address;self.shunt_ohms=float(shunt_ohms)
        self.calibration_id=calibration_id;self.device_id=device_id

    def _reg(self, register):
        # smbus2 swaps byte order compared with INA226 register on-wire 16-bit big-endian.
        raw=self.bus.read_word_data(self.address, register)
        return ((raw & 0xff) << 8) | ((raw >> 8) & 0xff)

    def sample(self, *, monotonic_seconds=None):
        import time
        shunt=self._reg(0x01)
        if shunt & 0x8000: shunt -= 65536
        bus=self._reg(0x02)
        volts=bus * 0.00125
        amps=(shunt * 2.5e-6) / self.shunt_ohms
        if amps < 0:
            raise ValueError("reverse current not modeled; fail closed")
        return PowerSample(time.monotonic() if monotonic_seconds is None else monotonic_seconds,
                           volts*amps, volts, amps, self.device_id,
                           "INA226_UNATTESTED", self.calibration_id)

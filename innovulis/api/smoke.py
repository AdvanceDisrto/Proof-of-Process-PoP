"""iNNOVULIS SPU mathematical and illustrative physics smoke gates.

No optical device is read. Outputs are model results with explicit assumptions.
"""
from __future__ import annotations
import hashlib
import math
import time
from dataclasses import dataclass
import numpy as np

H = 6.62607015e-34
C = 299792458.0
LAMBDA_M = 1550e-9
E_PHOTON = H * C / LAMBDA_M

@dataclass(frozen=True)
class Wavelet:
    amplitude: float
    phase: float
    wavelength_nm: float

    def field(self) -> complex:
        return self.amplitude * complex(math.cos(self.phase), math.sin(self.phase))


def superpose(waves: list[Wavelet]) -> dict[float, complex]:
    """Coherent summation of complex fields per exact simulated wavelength."""
    out: dict[float, complex] = {}
    for w in waves:
        out[w.wavelength_nm] = out.get(w.wavelength_nm, 0j) + w.field()
    return out


def phase_invert(w: Wavelet) -> Wavelet:
    """Physical phase rotation by pi, *not* Boolean NOT of amplitude encoding."""
    return Wavelet(w.amplitude, (w.phase + math.pi) % (2 * math.pi), w.wavelength_nm)


def boolean_and(a: int, b: int) -> int:
    """Thresholded coherent amplitude of two same-phase, same-channel symbols."""
    w = 1550.0
    field = superpose([Wavelet(float(a), 0, w), Wavelet(float(b), 0, w)])[w]
    return int(abs(field) > 1.5)


def boolean_xor(a: int, b: int) -> int:
    """Difference interferometer: a + (-b), not a+b thresholded."""
    w = 1550.0
    field = superpose([Wavelet(float(a), 0, w), Wavelet(float(b), math.pi, w)])[w]
    return int(abs(field) > 0.5)


def boolean_not(a: int) -> int:
    """Reference-arm complement: coherent 1-a, after thresholding."""
    w = 1550.0
    field = superpose([Wavelet(1.0, 0, w), Wavelet(float(a), math.pi, w)])[w]
    return int(abs(field) > 0.5)


def matmul_complex_field(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Complex-field addition preserving signed products; CPU model only."""
    if a.ndim != 2 or a.shape != b.shape or a.shape[0] != a.shape[1]:
        raise ValueError("expected equally sized square matrices")
    n = a.shape[0]
    out = np.zeros((n, n), dtype=np.int64)
    for i in range(n):
        for j in range(n):
            products = [int(a[i, k]) * int(b[k, j]) for k in range(n)]
            # A negative signed product is phase pi, positive is phase 0.
            waves = [Wavelet(abs(float(p)), math.pi if p < 0 else 0.0, 1550.0)
                     for p in products]
            z = superpose(waves)[1550.0]
            out[i, j] = round(z.real)
    return out


def run_cwa_smoke() -> dict:
    t0 = time.perf_counter()
    cases = [(0, 0), (0, 1), (1, 0), (1, 1)]
    gates = []
    gates.append({"gate": "AND truth table", "passed": all(boolean_and(a, b) == (a & b) for a, b in cases)})
    gates.append({"gate": "XOR differential truth table", "passed": all(boolean_xor(a, b) == (a ^ b) for a, b in cases)})
    gates.append({"gate": "NOT reference-arm truth table", "passed": all(boolean_not(a) == (1-a) for a in (0, 1))})
    w = Wavelet(0.75, 0.3, 1550.0)
    gates.append({"gate": "Phase inversion involution", "passed": abs(phase_invert(phase_invert(w)).field()-w.field()) < 1e-12})
    fields = superpose([Wavelet(1, 0, 1550), Wavelet(1, 0, 1310)])
    gates.append({"gate": "Ideal wavelength bucket isolation", "passed": len(fields) == 2 and all(abs(v-1) < 1e-12 for v in fields.values())})
    rng = np.random.default_rng(911)
    mismatch = 0
    for _ in range(64):
        a = rng.integers(-128, 128, (4, 4), dtype=np.int8)
        b = rng.integers(-128, 128, (4, 4), dtype=np.int8)
        mismatch += int(not np.array_equal(matmul_complex_field(a, b), a.astype(np.int64) @ b.astype(np.int64)))
    for a, b in [(np.eye(4, dtype=np.int8), np.full((4, 4), -128, dtype=np.int8)),
                 (np.full((4, 4), 127, dtype=np.int8), np.full((4, 4), -128, dtype=np.int8)),
                 (np.zeros((4, 4), dtype=np.int8), np.eye(4, dtype=np.int8))]:
        mismatch += int(not np.array_equal(matmul_complex_field(a, b), a.astype(np.int64) @ b.astype(np.int64)))
    gates.append({"gate": "Signed INT8 4x4 field matmul vs integer reference", "passed": mismatch == 0, "vectors": 67, "mismatches": mismatch})
    fixed = [Wavelet(0.7, 0.3, 1550), Wavelet(0.4, 1.1, 1550)]
    digests = {hashlib.sha256(str(superpose(fixed)[1550]).encode()).hexdigest() for _ in range(1000)}
    gates.append({"gate": "Software determinism 1000 replays", "passed": len(digests) == 1, "distinct_hashes": len(digests)})
    return {"schema": "innovulis/spu-cwa-model/v1", "execution_tier": "CPU_SIMULATION", "gates": gates,
            "gates_passed": sum(bool(g["passed"]) for g in gates), "gates_total": len(gates),
            "elapsed_ms": round((time.perf_counter()-t0)*1000, 3),
            "verdict": "PASS" if all(g["passed"] for g in gates) else "FAIL",
            "does_not_prove": ["photonic execution", "WDM cross-talk isolation in a real device", "optical power", "speedup", "hardware attestation"]}


def enob_from_amplitude_snr(snr: float) -> float:
    if snr <= 1:
        return 0.0
    return max(0.0, (20 * math.log10(snr) - 1.76) / 6.02)


def estimate_enob(photons: int, nep_w_per_sqrt_hz: float = 20e-12,
                  bandwidth_hz: float = 10e9, modulator_bits: float = 6,
                  adc_bits: float = 10) -> dict:
    optical_w = photons * E_PHOTON * bandwidth_hz
    shot = enob_from_amplitude_snr(math.sqrt(photons))
    thermal = enob_from_amplitude_snr(optical_w / (nep_w_per_sqrt_hz * math.sqrt(bandwidth_hz)))
    return {"photons_per_sample": photons, "optical_power_w": optical_w,
            "shot_limited_bits": round(shot, 3), "thermal_limited_bits": round(thermal, 3),
            "model_effective_bits": round(min(shot, thermal, modulator_bits, adc_bits), 3)}


def estimate_power(tia_mw: float = 50, detector_mw: float = 20) -> dict:
    components = {"laser_electrical_w": .1 / .2, "modulators_w": 64*.005,
                  "detectors_w": 64*detector_mw/1000, "tias_w": 64*tia_mw/1000,
                  "adcs_w": 64*.006, "dac_control_w": .5, "clock_dsp_w": 1.0}
    total = sum(components.values())
    tops = 2*64*64*10e9/1e12
    return {"assumed_components_w": components, "total_assumed_w": round(total, 3),
            "idealized_tops": round(tops, 3), "idealized_tops_per_w": round(tops/total, 3),
            "warning": "Assumed, not measured; excludes I/O, thermal, utilization, conversion overhead and accuracy equivalence."}


def run_spu_empirical() -> dict:
    """Run parameterized model checks, NOT empirical measurement."""
    enob = [estimate_enob(10**k) for k in range(2, 9)]
    power = estimate_power()
    # Isolation power ratios, converted to upper-bound amplitude SNR via sqrt.
    # Not a physical channel-count estimate; actual mixing depends on encoding.
    crosstalk = [{"leakage_power_db": db,
                  "idealized_amplitude_snr": round(10**(-db/20), 5),
                  "noise_only_enob_upper_bound": round(enob_from_amplitude_snr(10**(-db/20)), 3)}
                 for db in (-20, -30, -40, -50)]
    rng = np.random.default_rng(911)
    modes = 16
    t = (rng.standard_normal((modes, modes))+1j*rng.standard_normal((modes,modes)))/math.sqrt(2)
    challenge = rng.choice([-1, 1], size=modes)
    truth = t @ challenge
    attacks = []
    for k in (4, 8, 16, 32):
        x = rng.choice([-1, 1], size=(k, modes))
        response = x @ t.T
        fitted, *_ = np.linalg.lstsq(x, response, rcond=None)
        error = float(np.mean(np.abs(fitted.T @ challenge - truth)))
        attacks.append({"queries": k, "prediction_mae": round(error, 6),
                        "linear_model_reconstructed": bool(error < 1e-5)})
    assumptions = {"wavelength_nm": 1550, "bandwidth_hz": 10e9,
                   "nep_w_per_sqrt_hz": 20e-12, "modulator_effective_bits": 6,
                   "adc_effective_bits": 10,
                   "puf_model": "16-mode LINEAR transmission matrix; complex-field readout, no noise",
                   "crosstalk": "single interferer; power dB converted to field amplitude, no aggregation"}
    return {"schema": "innovulis/spu-physics-model/v1", "execution_tier": "CPU_PARAMETER_MODEL",
            "assumptions": assumptions,
            "results": {"enob_sweep": enob, "power_64x64": power, "crosstalk_model": crosstalk,
                        "chosen_challenge_linear_model": attacks,
                        "sensitivity": {"better_detector": estimate_enob(100000, nep_w_per_sqrt_hz=2e-12),
                                        "higher_modulator_precision": estimate_enob(100000, modulator_bits=8),
                                        "low_power_tia": estimate_power(tia_mw=5)}},
            "verdict": "MODEL_COMPUTED_NOT_MEASURED",
            "does_not_prove": ["actual device ENOB", "photonic device existence", "zero heat", "real WDM channel count", "security of any real PUF", "GPU comparison"]}

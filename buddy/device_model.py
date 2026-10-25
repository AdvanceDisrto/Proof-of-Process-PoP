"""Build a capability profile from a device probe."""
from .jcs import jcs, sha

def classify(probe: dict) -> str:
    if probe.get("simulated_class"):
        return probe["simulated_class"]
    cores, mem = probe.get("cores", 1), probe.get("memory_available_mb", 0)
    if mem < 2000: return "phone"
    if cores < 4: return "tv"
    if mem > 32000 and cores >= 8: return "server"
    return "laptop"

def precision_for(probe: dict) -> str:
    mem = probe.get("memory_available_mb", 0)
    feats = set(probe.get("features", []))
    if mem < 2000: return "int8"
    if "avx512f" in feats or "avx512" in feats: return "fp64"
    return "fp32"

def build_device_model(probe: dict) -> dict:
    class_ = classify(probe)
    precision = precision_for(probe)
    mem_mb = probe.get("memory_available_mb", 512)
    model = {
        "spec": "buddy-device/1.0",
        "class": class_,
        "compute": {"cores": probe.get("cores", 1), "arch": probe.get("arch", "unknown"),
                    "features": sorted(probe.get("features", []))},
        "memory": {"available_mb": mem_mb},
        "precision": precision,
        "limits": {"max_batch": max(1, min(64, mem_mb // 128)),
                   "max_context": max(128, min(8192, mem_mb * 2))},
        "interfaces": {"wifi": probe.get("has_wifi", False),
                        "ethernet": probe.get("has_ethernet", False)},
        "runtime": {"python": probe.get("python", "unknown"),
                    "containerized": probe.get("in_container", False),
                    "simulated": bool(probe.get("simulated_class"))},
    }
    model["device_hash"] = sha(jcs(model))
    return model

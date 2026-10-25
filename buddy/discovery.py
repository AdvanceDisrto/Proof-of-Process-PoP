"""Real device capabilities. Best effort, never fabricated."""
import os
import platform
import socket

def probe(override: dict | None = None) -> dict:
    if override is not None:
        return dict(override)
    cores = os.cpu_count() or 1
    arch = platform.machine()
    py = platform.python_version()
    features: list[str] = []
    try:
        if os.path.exists("/proc/cpuinfo"):
            text = open("/proc/cpuinfo").read().lower()
            for feat in ("avx512f", "avx512", "avx2", "avx", "fma", "sse4_2"):
                if feat in text:
                    features.append(feat)
    except Exception:
        pass
    mem_mb = 0
    try:
        if os.path.exists("/proc/meminfo"):
            for line in open("/proc/meminfo"):
                if line.startswith("MemAvailable:"):
                    mem_mb = int(line.split()[1]) // 1024
                    break
    except Exception:
        pass
    if not mem_mb:
        try:
            import psutil
            mem_mb = int(psutil.virtual_memory().available / (1024 * 1024))
        except Exception:
            mem_mb = 512
    ifaces: list[str] = []
    try:
        ifaces = [name for _, name in socket.if_nameindex()]
    except Exception:
        pass
    return {
        "arch": arch, "cores": cores, "memory_available_mb": mem_mb,
        "python": py, "features": sorted(set(features)),
        "interfaces": ifaces,
        "has_wifi": any(n.startswith(("wl", "wlan")) for n in ifaces),
        "has_ethernet": any(n.startswith(("en", "eth")) for n in ifaces),
        "in_container": os.path.exists("/.dockerenv"),
    }

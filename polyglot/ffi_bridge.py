from __future__ import annotations

import ctypes
import hashlib
from pathlib import Path


class IBareReceiptManifest(ctypes.Structure):
    _fields_ = [
        ("sequence_id", ctypes.c_uint64),
        ("timestamp_utc", ctypes.c_uint64),
        ("payload_hash", ctypes.c_ubyte * 32),
        ("platform_flags", ctypes.c_uint32),
    ]


class IBareBridge:
    def __init__(self, library: str | Path = "build/libibare.so") -> None:
        self.lib = ctypes.CDLL(str(library))
        self.lib.ibare_detect_architecture_flags.restype = ctypes.c_uint32
        self.lib.ibare_hash_bytes.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_ubyte),
        ]
        self.lib.ibare_hash_bytes.restype = ctypes.c_int
        self.lib.ibare_generate_deterministic_receipt.argtypes = [
            ctypes.POINTER(IBareReceiptManifest), ctypes.POINTER(ctypes.c_ubyte)
        ]
        self.lib.ibare_generate_deterministic_receipt.restype = ctypes.c_int

    def receipt(self, payload: bytes, timestamp_utc: int, sequence_id: int = 1) -> dict:
        payload_buf = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
        payload_hash = (ctypes.c_ubyte * 32)()
        if self.lib.ibare_hash_bytes(payload_buf, len(payload), payload_hash) != 0:
            raise RuntimeError("iBare payload hashing failed")
        python_hash = hashlib.sha256(payload).digest()
        if bytes(payload_hash) != python_hash:
            raise RuntimeError("C/Python SHA-256 mismatch")
        flags = int(self.lib.ibare_detect_architecture_flags())
        manifest = IBareReceiptManifest(
            sequence_id=sequence_id,
            timestamp_utc=timestamp_utc,
            payload_hash=payload_hash,
            platform_flags=flags,
        )
        out = (ctypes.c_ubyte * 32)()
        if self.lib.ibare_generate_deterministic_receipt(ctypes.byref(manifest), out) != 0:
            raise RuntimeError("iBare receipt generation failed")
        return {
            "spec": "innovulis-ibare-ffi/1.0",
            "state": "VERIFIED_PROCESS",
            "receipt_hash": "sha256:" + bytes(out).hex(),
            "payload_hash": "sha256:" + bytes(payload_hash).hex(),
            "platform_flags": flags,
            "physical_gate": "ACTION_REQUIRED",
            "does_not_prove": [
                "TPM quote or hardware-rooted attestation",
                "physical energy measurement",
                "CPU cycle count",
                "ASIC execution",
                "foundry fabrication",
            ],
        }

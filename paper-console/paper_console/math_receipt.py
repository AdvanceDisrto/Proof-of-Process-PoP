"""Actual numerical computation with inspectable input and output byte commitments."""
from __future__ import annotations
import hashlib
import math
import numpy as np


def compute_covariance_svd(image: np.ndarray, *, patch: int = 4) -> dict:
    """Real covariance/SVD of non-overlapping image patches; NOT medical diagnosis.

    Deterministic little-endian float64 hash across same NumPy data, no simulated AI.
    """
    x = np.asarray(image, dtype=np.float64)
    if x.ndim != 2 or not 4 <= x.shape[0] <= 4096 or not 4 <= x.shape[1] <= 4096:
        raise ValueError("expected 2D bounded image")
    if type(patch) is not int or patch < 2 or patch > 32:
        raise ValueError("invalid patch")
    if any(s % patch for s in x.shape):
        raise ValueError("image dimensions must divide into whole patches")
    if not np.isfinite(x).all():
        raise ValueError("image has non-finite pixels")
    blocks = x.reshape(x.shape[0] // patch, patch, x.shape[1] // patch, patch)
    rows = blocks.transpose(0, 2, 1, 3).reshape(-1, patch * patch)
    if len(rows) < 2:
        raise ValueError("covariance needs at least 2 patches")
    centered = rows - rows.mean(axis=0, keepdims=True)
    cov = centered.T @ centered / (len(rows) - 1)
    u, singular, vh = np.linalg.svd(cov, full_matrices=False)
    reconstructed = (u * singular) @ vh
    residual = np.linalg.norm(reconstructed - cov, ord="fro")
    scale = max(1.0, float(np.linalg.norm(cov, ord="fro")))
    if not np.all(np.isfinite(singular)) or residual > 1e-9 * scale:
        raise ArithmeticError("SVD reconstruction residual too large")
    def digest(arr):
        return hashlib.sha256(np.ascontiguousarray(arr, dtype="<f8").tobytes()).hexdigest()
    return {"algorithm": "numpy_covariance_svd_v1", "numpy_version": np.__version__,
            "image_shape": list(x.shape), "patch_size": patch, "patches": int(len(rows)),
            "input_f64le_sha256": digest(x), "covariance_f64le_sha256": digest(cov),
            "svd_u_f64le_sha256": digest(u), "svd_s_f64le_sha256": digest(singular),
            "svd_vh_f64le_sha256": digest(vh), "top_singular_values": singular[:3].tolist(),
            "reconstruction_residual": float(residual),
            "provenance": "LOCAL_REAL_NUMPY_COMPUTATION_NOT_INFERENCE_PROOF",
            "does_not_prove": ["model inference", "training", "medical diagnosis", "hardware work"]}

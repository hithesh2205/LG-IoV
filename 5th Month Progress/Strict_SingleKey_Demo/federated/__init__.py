"""Federated learning + homomorphic aggregation for FedIoV."""
from __future__ import annotations

from .fhe_adapter import (
    BACKENDS,
    CKKSVector,
    EncryptedScalar,
    PlaintextVector,
    build_ckks_context,
    encrypt_layerwise,
    encrypt_update,
    flatten_model,
    inject_layerwise,
    load_flat_into_model,
    multiplicative_depth,
)

__all__ = [
    "BACKENDS", "CKKSVector", "EncryptedScalar", "PlaintextVector",
    "build_ckks_context", "encrypt_layerwise", "encrypt_update",
    "flatten_model", "inject_layerwise", "load_flat_into_model",
    "multiplicative_depth",
]

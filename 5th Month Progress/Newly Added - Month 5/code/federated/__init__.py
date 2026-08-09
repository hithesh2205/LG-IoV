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
from .multikey_ckks import (
    MultiKeyContext,
    UserKeyShare,
    demonstrate_dropout_failure,
    verify_mask_cancellation,
)
from .partition import DirichletPartition, dirichlet_partition
from .secure_channel import IdentityKey, SecureChannel, handshake_pair
from .client import FederatedClient
from .server import (
    AggregationAudit,
    FederatedServer,
    assert_no_individual_decryption,
)

__all__ = [
    "BACKENDS", "CKKSVector", "EncryptedScalar", "PlaintextVector",
    "build_ckks_context", "encrypt_layerwise", "encrypt_update",
    "flatten_model", "inject_layerwise", "load_flat_into_model",
    "multiplicative_depth",
    "MultiKeyContext", "UserKeyShare",
    "demonstrate_dropout_failure", "verify_mask_cancellation",
    "DirichletPartition", "dirichlet_partition",
    "IdentityKey", "SecureChannel", "handshake_pair",
    "FederatedClient", "FederatedServer",
    "AggregationAudit", "assert_no_individual_decryption",
]

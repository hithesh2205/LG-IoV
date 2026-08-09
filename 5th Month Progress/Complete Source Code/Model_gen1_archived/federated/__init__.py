"""FedIoV federated layer — Phase 1 components.

This package wraps the local ``KANConvNet`` classifier into the federated
pipeline described in Heidari et al., FedIoV (FGCS 2026):

* :mod:`partition`      — Dirichlet (α=0.3) non-IID client sharding.
* :mod:`secure_channel` — ECDH-P256 handshake + AES-256-GCM channel
                          with Ed25519 mutual authentication.
* :mod:`server`         — Global model init + broadcast to N clients.
* :mod:`ga_config`      — Genetic-algorithm hyperparameter search space
                          + population initialisation (population size N,
                          generations G=20).

Phase 1 only sets up these components; the federated training rounds,
TOPSIS+Multi-Krum aggregation, and GA evolution loop are Phase 2+.
"""

from .partition import DirichletPartition, dirichlet_partition
from .secure_channel import (
    SecureChannel, IdentityKey,
    handshake, complete_handshake, handshake_pair,
)
from .server import FederatedServer, broadcast_state_dict
from .ga_config import GAConfig, init_population, sample_individual

__all__ = [
    "DirichletPartition", "dirichlet_partition",
    "SecureChannel", "IdentityKey", "handshake",
    "FederatedServer", "broadcast_state_dict",
    "GAConfig", "init_population", "sample_individual",
]

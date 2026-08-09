"""Low-level cryptographic primitives.

Currently the negacyclic NTT reference implementation that the embedded
C/NEON kernel is ported from and validated against.
"""
from __future__ import annotations

from .ntt import (
    NTTContext,
    bit_reverse_indices,
    export_test_vectors,
    find_ntt_prime,
    is_prime,
    negacyclic_convolution_schoolbook,
    primitive_root,
)

__all__ = [
    "NTTContext", "bit_reverse_indices", "export_test_vectors",
    "find_ntt_prime", "is_prime", "negacyclic_convolution_schoolbook",
    "primitive_root",
]

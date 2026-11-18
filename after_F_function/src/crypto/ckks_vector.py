"""CKKS and Plaintext Vector Wrappers with Whole-Vector SIMD Packing."""
from __future__ import annotations

from typing import List, Optional, Union, Any
import numpy as np
import tenseal as ts

DEFAULT_SLOT_COUNT = 4096


class CKKSVector:
    """Homomorphically encrypted parameter vector packed across SIMD ciphertext chunks."""

    def __init__(
        self,
        context: ts.Context,
        data: Optional[np.ndarray] = None,
        chunks: Optional[List[ts.CKKSVector]] = None,
        n_values: Optional[int] = None,
        slot_count: int = DEFAULT_SLOT_COUNT,
    ) -> None:
        self.context = context
        self.slot_count = int(slot_count)

        if chunks is not None:
            self._chunks = chunks
            self.n_values = int(n_values) if n_values is not None else 0
        else:
            vec = np.asarray(data, dtype=np.float64).ravel()
            self.n_values = int(vec.size)
            n_chunks = max(1, int(np.ceil(self.n_values / self.slot_count)))
            self._chunks = [
                ts.ckks_vector(
                    context,
                    vec[i * self.slot_count:(i + 1) * self.slot_count].tolist(),
                )
                for i in range(n_chunks)
            ]

    @property
    def num_chunks(self) -> int:
        return len(self._chunks)

    def __add__(self, other: Union[CKKSVector, Any]) -> CKKSVector:
        if isinstance(other, CKKSVector):
            if len(self._chunks) != len(other._chunks):
                raise ValueError("Mismatch in number of ciphertext chunks.")
            added_chunks = [a + b for a, b in zip(self._chunks, other._chunks)]
            return CKKSVector(
                self.context, chunks=added_chunks, n_values=self.n_values, slot_count=self.slot_count
            )
        raise TypeError("CKKSVector can only be added to another CKKSVector.")

    def __mul__(self, scalar: Union[int, float]) -> CKKSVector:
        s = float(scalar)
        scaled_chunks = [c * s for c in self._chunks]
        return CKKSVector(
            self.context, chunks=scaled_chunks, n_values=self.n_values, slot_count=self.slot_count
        )

    __rmul__ = __mul__

    def decrypt(self, secret_context: Optional[ts.Context] = None) -> np.ndarray:
        """Decrypt all chunks and concatenate into 1D numpy array."""
        ctx = secret_context if secret_context is not None else self.context
        parts = []
        for c in self._chunks:
            c_copy = c.copy()
            if not c_copy.context().is_private() and ctx.is_private():
                c_copy.link_context(ctx)
            parts.append(np.asarray(c_copy.decrypt(), dtype=np.float64))
        return np.concatenate(parts)[:self.n_values]

    def serialized_bytes(self) -> int:
        return sum(len(c.serialize()) for c in self._chunks)

    def serialize(self) -> List[bytes]:
        return [c.serialize() for c in self._chunks]

    @classmethod
    def deserialize(
        cls, context: ts.Context, raw_chunks: List[bytes], n_values: int, slot_count: int = DEFAULT_SLOT_COUNT
    ) -> CKKSVector:
        chunks = [ts.ckks_vector_from(context, b) for b in raw_chunks]
        return cls(context, chunks=chunks, n_values=n_values, slot_count=slot_count)


class PlaintextVector:
    """Plaintext parameter vector mirror providing the identical interface for Experiment A."""

    def __init__(self, data: np.ndarray) -> None:
        self.data = np.asarray(data, dtype=np.float64).ravel()
        self.n_values = int(self.data.size)

    @property
    def num_chunks(self) -> int:
        return 1

    def __add__(self, other: Union[PlaintextVector, np.ndarray]) -> PlaintextVector:
        if isinstance(other, PlaintextVector):
            return PlaintextVector(self.data + other.data)
        return PlaintextVector(self.data + np.asarray(other, dtype=np.float64))

    def __mul__(self, scalar: Union[int, float]) -> PlaintextVector:
        return PlaintextVector(self.data * float(scalar))

    __rmul__ = __mul__

    def decrypt(self, secret_context: Optional[Any] = None) -> np.ndarray:
        return self.data.copy()

    def serialized_bytes(self) -> int:
        return int(self.data.size * 4)  # 4 bytes per float32 representation

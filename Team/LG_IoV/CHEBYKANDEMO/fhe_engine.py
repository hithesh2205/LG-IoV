"""
fhe_engine.py
=============
Real CKKS Fully-Homomorphic Encryption engine built on TenSEAL.

This module provides:
  - CKKSContextManager : create / serialise CKKS contexts, encrypt & decrypt tensors.
  - DesignatedDecryptor : protocol-level holder of the secret key.
  - LayerWiseEncryptor  : encrypt / decrypt every named parameter of a PyTorch model.
  - EncryptedTensor     : lightweight dataclass carried between encrypt ↔ decrypt.
  - Helper utilities    : depth calculator, context logger.

NO simulation, NO mock encryption.  If TenSEAL is missing the module
raises ``RuntimeError`` at import time.
"""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

# ── hard dependency on real TenSEAL ─────────────────────────────────────────
try:
    import tenseal as ts
except ImportError as exc:
    raise RuntimeError(
        "TenSEAL is required for CKKS FHE.  "
        "Install with:  pip install tenseal>=0.3.14"
    ) from exc
# ─────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Data-class for encrypted parameter bundles
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@dataclass
class EncryptedTensor:
    """Container that pairs a CKKS cipher-text with the metadata needed to
    reconstruct the original ``torch.Tensor`` after decryption.

    Attributes:
        vector: The encrypted CKKS vector (``ts.CKKSVector``).
        shape:  Original tensor shape so we can ``view()`` back after decrypt.
        numel:  Number of scalar elements in the original tensor.
        name:   Human-readable parameter name (e.g. ``"layer1.weight"``).
    """

    vector: ts.CKKSVector
    shape: Tuple[int, ...]
    numel: int
    name: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper utilities
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def compute_required_depth(n_clients: int, byzantine_tolerance: int) -> int:
    """Compute the minimum CKKS multiplicative depth for FedAvg + Multi-Krum.

    FedAvg itself only needs depth-1 (weighted sum of cipher-texts).
    Multi-Krum adds one more level when computing pairwise score products,
    so in practice we need **depth ≥ 2**.

    If future aggregation schemes require deeper circuits, callers may
    increase the returned value.

    Args:
        n_clients:           Total number of federated clients.
        byzantine_tolerance: Maximum number of Byzantine (malicious) clients
                             tolerated by Multi-Krum (parameter *f*).

    Returns:
        Recommended multiplicative depth (int, ≥ 2).

    Raises:
        ValueError: If the tolerance is too large for the client pool.
    """
    logger.debug(
        "compute_required_depth called: n_clients=%d, byzantine_tolerance=%d",
        n_clients,
        byzantine_tolerance,
    )
    if byzantine_tolerance < 0:
        raise ValueError(
            f"byzantine_tolerance must be non-negative, got {byzantine_tolerance}"
        )
    if n_clients < 2 * byzantine_tolerance + 3:
        raise ValueError(
            f"Multi-Krum requires n_clients >= 2*f + 3.  "
            f"Got n_clients={n_clients}, f={byzantine_tolerance} → need >= {2 * byzantine_tolerance + 3}."
        )

    # depth 1 for weighted averaging, +1 for Krum score computation
    depth = 2
    logger.info(
        "Recommended CKKS depth for %d clients (f=%d): %d",
        n_clients,
        byzantine_tolerance,
        depth,
    )
    return depth


def log_context_params(context: ts.Context) -> None:
    """Log the salient parameters of a TenSEAL CKKS context.

    Args:
        context: A ``ts.Context`` instance (public or secret-key).
    """
    has_sk = context.has_secret_key()
    logger.info(
        "TenSEAL CKKS context — has_secret_key=%s",
        has_sk,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CKKS Context Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class CKKSContextManager:
    """Creates and manages a TenSEAL CKKS encryption context.

    The *full* context retains the secret key and is used for key-holder
    operations (encrypt / decrypt).  A *public* copy — serialised then
    deserialised without the secret key — is distributed to clients that
    only need to encrypt.

    Args:
        poly_modulus_degree: Degree of the cyclotomic polynomial (power of 2).
            Larger values ⇒ more slots but slower operations.  Default 8192.
        coeff_mod_bit_sizes: Bit-size list for the coefficient modulus chain.
            Default ``[60, 40, 40, 60]`` → multiplicative depth 2.
        global_scale: Scale factor for encoding (default ``2**40``).
    """

    def __init__(
        self,
        poly_modulus_degree: int = 8192,
        coeff_mod_bit_sizes: Optional[List[int]] = None,
        global_scale: float = 2**40,
    ) -> None:
        logger.info("CKKSContextManager.__init__  BEGIN")

        if coeff_mod_bit_sizes is None:
            coeff_mod_bit_sizes = [60, 40, 40, 60]

        # Validate inputs
        assert (
            poly_modulus_degree & (poly_modulus_degree - 1) == 0
        ), f"poly_modulus_degree must be a power of 2, got {poly_modulus_degree}"
        assert (
            len(coeff_mod_bit_sizes) >= 3
        ), "Need at least 3 coeff_mod entries for depth ≥ 1"
        assert global_scale > 0, "global_scale must be positive"

        self._poly_modulus_degree: int = poly_modulus_degree
        self._coeff_mod_bit_sizes: List[int] = list(coeff_mod_bit_sizes)
        self._global_scale: float = global_scale

        # Multiplicative depth = #interior primes = len(chain) - 2
        self._mult_depth: int = len(coeff_mod_bit_sizes) - 2
        logger.info(
            "Coefficient modulus chain: %s  →  multiplicative depth = %d",
            coeff_mod_bit_sizes,
            self._mult_depth,
        )

        # Build the CKKS context
        self._context: ts.Context = ts.context(
            scheme=ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes,
        )
        self._context.global_scale = global_scale
        self._context.generate_galois_keys()
        self._context.generate_relin_keys()

        assert self._context.has_secret_key(), (
            "Context must have a secret key immediately after creation."
        )

        log_context_params(self._context)
        logger.info("CKKSContextManager.__init__  END")

    # ── properties ───────────────────────────────────────────────────────
    @property
    def context(self) -> ts.Context:
        """Return the *full* context (includes the secret key)."""
        return self._context

    @property
    def multiplicative_depth(self) -> int:
        """Return the computed multiplicative depth."""
        return self._mult_depth

    @property
    def poly_modulus_degree(self) -> int:
        """Return the polynomial modulus degree."""
        return self._poly_modulus_degree

    @property
    def coeff_mod_bit_sizes(self) -> List[int]:
        """Return a copy of the coefficient-modulus bit-size list."""
        return list(self._coeff_mod_bit_sizes)

    @property
    def global_scale(self) -> float:
        """Return the encoding scale."""
        return self._global_scale

    # ── public context ───────────────────────────────────────────────────
    def create_public_context(self) -> ts.Context:
        """Serialise the context *without* the secret key and deserialise
        it into a new ``ts.Context`` that can only encrypt, never decrypt.

        Returns:
            A public-only ``ts.Context``.

        Raises:
            AssertionError: If the returned context still has a secret key.
        """
        logger.info("create_public_context  BEGIN")

        # Make the context serialisable (drop secret key from serialisation)
        self._context.make_context_public()

        serialised: bytes = self._context.serialize()
        public_ctx: ts.Context = ts.context_from(serialised)

        assert not public_ctx.has_secret_key(), (
            "Public context must NOT contain a secret key."
        )

        # Re-create the full context so that the manager can still decrypt
        # (make_context_public mutated in-place, so we rebuild).
        self._context = ts.context(
            scheme=ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=self._poly_modulus_degree,
            coeff_mod_bit_sizes=self._coeff_mod_bit_sizes,
        )
        self._context.global_scale = self._global_scale
        self._context.generate_galois_keys()
        self._context.generate_relin_keys()

        log_context_params(public_ctx)
        logger.info("create_public_context  END  (has_secret_key=%s)", public_ctx.has_secret_key())
        return public_ctx

    # ── encrypt / decrypt helpers ────────────────────────────────────────
    def encrypt_tensor(self, tensor: torch.Tensor) -> ts.CKKSVector:
        """Encrypt a PyTorch tensor using the **full** (secret-key) context.

        The tensor is flattened to 1-D before encryption.

        Args:
            tensor: Arbitrary-shape ``torch.Tensor`` (float32 or float64).

        Returns:
            A ``ts.CKKSVector`` containing the encrypted values.
        """
        assert self._context.has_secret_key(), (
            "encrypt_tensor requires the full context with secret key."
        )
        flat: List[float] = tensor.detach().cpu().flatten().tolist()
        logger.debug(
            "encrypt_tensor: encrypting %d values (shape %s)",
            len(flat),
            tuple(tensor.shape),
        )
        ckks_vec: ts.CKKSVector = ts.ckks_vector(self._context, flat)
        logger.debug("encrypt_tensor: done — vector length %d", ckks_vec.size())
        return ckks_vec

    def decrypt_vector(self, ckks_vector: ts.CKKSVector) -> List[float]:
        """Decrypt a ``CKKSVector`` using the full (secret-key) context.

        Args:
            ckks_vector: An encrypted CKKS vector.

        Returns:
            List of decrypted float values.
        """
        assert self._context.has_secret_key(), (
            "decrypt_vector requires the full context with secret key."
        )
        ckks_vector.link_context(self._context)
        plaintext: List[float] = ckks_vector.decrypt()
        logger.debug("decrypt_vector: decrypted %d values", len(plaintext))
        return plaintext

    def encrypt_tensor_public(
        self, tensor: torch.Tensor, public_ctx: ts.Context
    ) -> ts.CKKSVector:
        """Encrypt a tensor using a **public-only** context.

        This is the path used by clients that never see the secret key.

        Args:
            tensor:     Arbitrary-shape ``torch.Tensor``.
            public_ctx: A context created by ``create_public_context()``.

        Returns:
            An encrypted ``ts.CKKSVector``.

        Raises:
            AssertionError: If ``public_ctx`` has a secret key (safety check).
        """
        assert not public_ctx.has_secret_key(), (
            "encrypt_tensor_public must receive a public-only context."
        )
        flat: List[float] = tensor.detach().cpu().flatten().tolist()
        logger.debug(
            "encrypt_tensor_public: encrypting %d values (shape %s)",
            len(flat),
            tuple(tensor.shape),
        )
        ckks_vec: ts.CKKSVector = ts.ckks_vector(public_ctx, flat)
        logger.debug(
            "encrypt_tensor_public: done — vector length %d", ckks_vec.size()
        )
        return ckks_vec


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Designated Decryptor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DesignatedDecryptor:
    """Protocol-level holder of the CKKS secret key.

    In the FedIoV protocol the *server* never possesses the secret key.
    Only this ``DesignatedDecryptor`` (typically owned by a trusted
    third-party or the key-ceremony output) can decrypt cipher-texts.

    Args:
        context_manager: A fully-initialised ``CKKSContextManager`` whose
            context still holds the secret key.
    """

    def __init__(self, context_manager: CKKSContextManager) -> None:
        logger.info("DesignatedDecryptor.__init__  BEGIN")
        assert context_manager.context.has_secret_key(), (
            "DesignatedDecryptor requires a context with the secret key."
        )
        self._secret_context: ts.Context = context_manager.context
        logger.info("DesignatedDecryptor.__init__  END  (secret key held)")

    def decrypt(self, ckks_vector: ts.CKKSVector) -> List[float]:
        """Decrypt a single ``CKKSVector``.

        The vector is first linked to the secret-key context so that
        TenSEAL can locate the decryption key.

        Args:
            ckks_vector: Encrypted CKKS vector.

        Returns:
            Decrypted list of floats.
        """
        logger.debug("DesignatedDecryptor.decrypt  BEGIN  (vector size=%d)", ckks_vector.size())
        ckks_vector.link_context(self._secret_context)
        plaintext: List[float] = ckks_vector.decrypt()
        logger.debug(
            "DesignatedDecryptor.decrypt  END  (decrypted %d values)",
            len(plaintext),
        )
        return plaintext


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Layer-wise Encryptor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LayerWiseEncryptor:
    """Encrypts and decrypts every named parameter of a ``torch.nn.Module``
    independently, yielding one ``EncryptedTensor`` per parameter.

    This *layer-wise* strategy (as opposed to flattening the entire model
    into one vector) allows the server to aggregate individual layers
    without touching the full parameter vector, and it keeps cipher-text
    sizes within CKKS slot limits.
    """

    def __init__(self) -> None:
        logger.info("LayerWiseEncryptor.__init__")

    # ── encrypt ──────────────────────────────────────────────────────────
    def encrypt_model(
        self, model: nn.Module, context: ts.Context
    ) -> Dict[str, EncryptedTensor]:
        """Encrypt all named parameters of *model* layer-by-layer.

        Each parameter tensor is flattened and encrypted as a separate
        ``ts.CKKSVector``.

        Args:
            model:   A PyTorch model whose parameters should be encrypted.
            context: A ``ts.Context`` (may be public-only or full).

        Returns:
            Dictionary mapping ``param_name`` → ``EncryptedTensor``.
        """
        logger.info("encrypt_model  BEGIN  (model type: %s)", type(model).__name__)
        encrypted_params: Dict[str, EncryptedTensor] = {}

        for name, param in model.named_parameters():
            flat: List[float] = param.detach().cpu().flatten().tolist()
            numel: int = param.numel()
            shape: Tuple[int, ...] = tuple(param.shape)

            logger.debug(
                "encrypt_model: encrypting param '%s'  shape=%s  numel=%d",
                name,
                shape,
                numel,
            )

            ckks_vec: ts.CKKSVector = ts.ckks_vector(context, flat)

            encrypted_params[name] = EncryptedTensor(
                vector=ckks_vec,
                shape=shape,
                numel=numel,
                name=name,
            )
            logger.debug(
                "encrypt_model: param '%s' encrypted — vector length %d",
                name,
                ckks_vec.size(),
            )

        logger.info(
            "encrypt_model  END  (%d parameters encrypted)", len(encrypted_params)
        )
        return encrypted_params

    # ── decrypt ──────────────────────────────────────────────────────────
    def decrypt_model(
        self,
        encrypted_params: Dict[str, EncryptedTensor],
        decryptor: DesignatedDecryptor,
        reference_model: nn.Module,
    ) -> nn.Module:
        """Decrypt every encrypted parameter and load them into a fresh
        copy of *reference_model*.

        Args:
            encrypted_params: Mapping returned by ``encrypt_model``.
            decryptor:        ``DesignatedDecryptor`` that holds the secret key.
            reference_model:  A model with the **same architecture** used
                              during encryption.  A ``deepcopy`` is made so
                              the original is never mutated.

        Returns:
            A new ``nn.Module`` with decrypted weights loaded.
        """
        logger.info("decrypt_model  BEGIN  (%d parameters)", len(encrypted_params))
        reconstructed: nn.Module = copy.deepcopy(reference_model)
        state_dict = reconstructed.state_dict()

        for name, enc_tensor in encrypted_params.items():
            logger.debug(
                "decrypt_model: decrypting param '%s'  (numel=%d, shape=%s)",
                name,
                enc_tensor.numel,
                enc_tensor.shape,
            )
            plaintext: List[float] = decryptor.decrypt(enc_tensor.vector)

            # TenSEAL may pad the plaintext to the next power-of-two slot
            # count, so we truncate to the original number of elements.
            truncated: List[float] = plaintext[: enc_tensor.numel]
            assert len(truncated) == enc_tensor.numel, (
                f"Expected {enc_tensor.numel} values for '{name}', "
                f"got {len(truncated)} after truncation."
            )

            tensor: torch.Tensor = torch.tensor(
                truncated, dtype=torch.float32
            ).view(enc_tensor.shape)
            state_dict[name] = tensor

            logger.debug(
                "decrypt_model: param '%s' restored  shape=%s",
                name,
                tuple(tensor.shape),
            )

        reconstructed.load_state_dict(state_dict)
        logger.info("decrypt_model  END")
        return reconstructed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Module-level convenience
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
__all__: List[str] = [
    "CKKSContextManager",
    "DesignatedDecryptor",
    "LayerWiseEncryptor",
    "EncryptedTensor",
    "compute_required_depth",
    "log_context_params",
]

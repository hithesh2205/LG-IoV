"""CKKS Encryption Context and Key Management Abstractions."""
from __future__ import annotations

from typing import Sequence, Optional
import tenseal as ts


DEFAULT_POLY_MODULUS_DEGREE = 8192
DEFAULT_COEFF_MOD_BIT_SIZES = [60, 40, 40, 60]
DEFAULT_GLOBAL_SCALE_BITS = 40


class KeyManager:
    """Manages CKKS key generation, public context separation, and decryption authorization."""

    def __init__(
        self,
        poly_modulus_degree: int = DEFAULT_POLY_MODULUS_DEGREE,
        coeff_mod_bit_sizes: Optional[Sequence[int]] = None,
        global_scale_bits: int = DEFAULT_GLOBAL_SCALE_BITS,
    ) -> None:
        if coeff_mod_bit_sizes is None:
            coeff_mod_bit_sizes = DEFAULT_COEFF_MOD_BIT_SIZES

        # Generate complete context holding secret key
        self.secret_context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=list(coeff_mod_bit_sizes),
        )
        self.secret_context.global_scale = 2 ** global_scale_bits
        self.secret_context.generate_galois_keys()
        self.secret_context.generate_relin_keys()

        # Public context: secret key stripped (safe for clients and RSU)
        self.public_context = ts.context_from(
            self.secret_context.serialize(save_secret_key=False)
        )
        self.poly_modulus_degree = int(poly_modulus_degree)
        self.slot_count = self.poly_modulus_degree // 2


def create_ckks_key_manager(
    poly_modulus_degree: int = DEFAULT_POLY_MODULUS_DEGREE,
    coeff_mod_bit_sizes: Optional[Sequence[int]] = None,
    global_scale_bits: int = DEFAULT_GLOBAL_SCALE_BITS,
) -> KeyManager:
    """Create a new KeyManager instance."""
    return KeyManager(
        poly_modulus_degree=poly_modulus_degree,
        coeff_mod_bit_sizes=coeff_mod_bit_sizes,
        global_scale_bits=global_scale_bits,
    )

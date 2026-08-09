import tenseal as ts
import torch
import numpy as np

class DesignatedDecryptor:
    """
    Holds the full CKKS context including the Secret Key.
    """
    def __init__(self):
        # Setup TenSEAL context
        # poly_modulus_degree=8192 and coeff_mod=[60, 40, 40, 60] gives a multiplicative depth of 2.
        # We need depth 1 (scalar mult for FedAvg + sum of squares for MultiKrum)
        # without chaining them.
        self.context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=8192,
            coeff_mod_bit_sizes=[60, 40, 40, 60]
        )
        self.context.global_scale = 2**40
        self.context.generate_galois_keys()
        self.context.generate_relin_keys()
        
    def get_public_context(self):
        """Returns a copy of the context with the secret key dropped."""
        public_context = self.context.copy()
        public_context.make_context_public()
        assert not public_context.has_secret_key(), "Public context must not have a secret key!"
        return public_context
        
    def decrypt_tensor(self, ckks_vector, shape):
        """Decrypts a CKKSVector and reshapes it back to a PyTorch tensor."""
        ckks_vector.link_context(self.context)
        decrypted_flat = ckks_vector.decrypt()
        # TenSEAL CKKS vectors might have trailing zeros due to polynomial degree packing
        numel = np.prod(shape)
        decrypted_flat = decrypted_flat[:numel]
        tensor = torch.tensor(decrypted_flat).view(shape)
        return tensor

def encrypt_tensor(tensor, context):
    """Encrypts a PyTorch tensor layer-wise into a TenSEAL CKKSVector."""
    flat_data = tensor.flatten().tolist()
    return ts.ckks_vector(context, flat_data)

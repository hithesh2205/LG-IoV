"""FHE Adapter for FedIoV

This module provides the necessary utilities to bridge the KANConvNet PyTorch model
with a Fully Homomorphic Encryption (FHE) library like TenSEAL or SEAL.

Your partner can use these utilities to extract the model's weights as a flat
1D vector, encrypt them on the client, perform encrypted aggregation on the server,
decrypt them back on the client, and load them back into the PyTorch model.
"""
from __future__ import annotations

import torch
import torch.nn as nn


def extract_flat_weights(model: nn.Module) -> torch.Tensor:
    """
    Extracts all learnable parameters (weights and biases) from the model
    and flattens them into a single 1D tensor.
    
    The partner will take this 1D tensor, convert it to a list or numpy array,
    and encrypt it using FHE (e.g., TenSEAL CKKS vector).
    
    Returns:
        1D torch.Tensor containing all parameters.
        For the default KANConvNet, this will have length 145,668.
    """
    params = [p.data.view(-1) for p in model.parameters() if p.requires_grad]
    return torch.cat(params)


def inject_flat_weights(model: nn.Module, flat_weights: torch.Tensor) -> None:
    """
    Takes a 1D tensor (e.g., the decrypted FHE vector) and injects the 
    values back into the model's parameter shapes.
    
    Args:
        model: The KANConvNet model.
        flat_weights: The 1D tensor of weights to load.
    """
    expected_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if flat_weights.numel() != expected_params:
        raise ValueError(
            f"Size mismatch: Expected {expected_params} parameters, "
            f"but got {flat_weights.numel()}."
        )

    offset = 0
    for p in model.parameters():
        if p.requires_grad:
            numel = p.numel()
            # Extract the slice for this parameter and reshape it
            p_slice = flat_weights[offset : offset + numel].view_as(p.data)
            p.data.copy_(p_slice)
            offset += numel


# ==============================================================================
# TEMPLATES FOR YOUR PARTNER TO FILL IN
# ==============================================================================

class FHEServerTemplate:
    """Template for the Server-side FHE operations."""
    
    def __init__(self):
        # TODO (Partner): The server should hold the FHE Public Context 
        # (Galois keys / Relin keys for operations) but NOT the Secret Key.
        pass

    def aggregate_encrypted_updates(self, encrypted_vectors: list):
        """
        Server aggregates the encrypted weights from clients.
        Since FHE is used, this is just encrypted vector addition.
        
        Args:
            encrypted_vectors: List of FHE ciphertext objects (e.g., tenseal.CKKSVector)
        
        Returns:
            The aggregated FHE ciphertext object.
        """
        # TODO (Partner): Implement FHE addition:
        # aggregated = encrypted_vectors[0]
        # for vec in encrypted_vectors[1:]:
        #     aggregated += vec
        # return aggregated * (1.0 / len(encrypted_vectors))
        pass


class FHEClientTemplate:
    """Template for the Client-side FHE operations."""
    
    def __init__(self, model: nn.Module):
        self.model = model
        # TODO (Partner): The client must hold the FHE Secret Key to decrypt 
        # the global model and the Public Context to encrypt its local updates.
    
    def encrypt_local_update(self) -> list:
        """
        Flattens the local model and encrypts it.
        """
        flat_tensor = extract_flat_weights(self.model)
        # Convert to list for TenSEAL compatibility
        flat_list = flat_tensor.cpu().numpy().tolist()
        
        # TODO (Partner): Encrypt using FHE.
        # NOTE: 145,668 is larger than the max slots for a standard CKKS 
        # ciphertext (usually 8192 or 16384). You will need to chunk `flat_list` 
        # into multiple ciphertexts.
        # 
        # chunk_size = 16384
        # encrypted_chunks = [
        #    tenseal.ckks_vector(self.context, flat_list[i:i + chunk_size])
        #    for i in range(0, len(flat_list), chunk_size)
        # ]
        # return encrypted_chunks
        pass

    def apply_global_model(self, encrypted_global_chunks: list):
        """
        Decrypts the aggregated model received from the server and loads it.
        """
        # TODO (Partner): Decrypt using FHE Secret Key
        # decrypted_list = []
        # for chunk in encrypted_global_chunks:
        #     decrypted_list.extend(chunk.decrypt(self.secret_key))
        
        # Convert back to tensor and inject
        # flat_tensor = torch.tensor(decrypted_list, dtype=torch.float32)
        # inject_flat_weights(self.model, flat_tensor)
        pass

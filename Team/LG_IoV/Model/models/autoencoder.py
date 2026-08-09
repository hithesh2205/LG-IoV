"""Convolutional Autoencoder for Unsupervised IDS (FHE-compatible).

As defined in the FHE integration track, this replaces the supervised KANConvNet
with an unsupervised Autoencoder. It is trained only on "normal" (Attack-free) CAN data.
Anomalies are detected at inference time when the reconstruction error (MSE)
exceeds a learned threshold.

This model is designed to have roughly 50,000 parameters to match the FHE track's
expectations for the CKKS scheme polynomial degree.
"""
import torch
import torch.nn as nn

class ConvAutoencoder(nn.Module):
    """A lightweight 1D Convolutional Autoencoder."""
    
    def __init__(self, in_channels: int = 46):
        super().__init__()
        self.in_channels = in_channels
        
        # Encoder (3 Conv layers)
        self.encoder = nn.Sequential(
            nn.Conv1d(in_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv1d(32, 64, kernel_size=3, padding=1, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(64, 64, kernel_size=3, padding=1, stride=2),
            nn.ReLU(inplace=True)
        )
        
        # Decoder (3 Conv layers)
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(64, 64, kernel_size=3, padding=1, stride=2, output_padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose1d(64, 32, kernel_size=3, padding=1, stride=2, output_padding=1),
            nn.ReLU(inplace=True),
            nn.Conv1d(32, in_channels, kernel_size=3, padding=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: shape (B, F) or (B, F, W)
        """
        # If input is flat (B, F), expand to (B, F, 1) for Conv1d
        is_flat = False
        if x.dim() == 2:
            x = x.unsqueeze(-1)
            is_flat = True
            
        z = self.encoder(x)
        out = self.decoder(z)
        
        # Handle sequence length mismatches from transpose padding
        if out.shape[-1] != x.shape[-1]:
            out = out[..., :x.shape[-1]]
            
        if is_flat:
            out = out.squeeze(-1)
            
        return out

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

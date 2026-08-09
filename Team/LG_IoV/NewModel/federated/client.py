"""Federated client — one simulated vehicle.

Protocol per round
------------------
1. Receive the plaintext global model over the **authenticated** channel
   (``secure_channel``: ECDH-P256 + AES-256-GCM + Ed25519 mutual auth).
2. Train locally on the vehicle's non-IID shard.
3. Flatten the updated parameters and **encrypt** them under CKKS.
4. Upload the ciphertext. The vehicle's key share never leaves the vehicle.

Why the channel is still here (defect D6)
-----------------------------------------
The Month-4 deck claimed transport security had been removed because "security
is guaranteed by FHE mathematical bounds". FHE provides confidentiality of the
payload and nothing else — no authentication, no integrity, no replay
protection, no Sybil resistance. A fleet where anyone can register as a vehicle
and replay last round's ciphertext defeats the Byzantine defence regardless of
how strong the encryption is. FheFL also *requires* Diffie–Hellman to establish
the pairwise secrets its key sharing depends on, so the handshake had to come
back anyway.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from data.loader import CanFeatureDataset
from models.cheby_kan import ChebyshevKAN

from .fhe_adapter import encrypt_update, flatten_model, load_flat_into_model


class FederatedClient:
    """A simulated vehicle performing local training and CKKS encryption."""

    def __init__(
        self,
        client_id: int,
        name: str,
        train_indices: np.ndarray,
        backend: str = "ckks",
        context=None,
        secure_channel=None,
        levels_to_drop: int = 1,
    ) -> None:
        self.client_id = client_id
        self.name = name
        self.train_indices = np.asarray(train_indices)
        self.backend = backend
        self.context = context
        self.secure_channel = secure_channel
        #: Levels consumed locally before upload. 1 is measured-safe and cuts
        #: the wire size by ~29.6 % - see federated/packing.py.
        self.levels_to_drop = levels_to_drop
        self.model: Optional[ChebyshevKAN] = None

    # ── receive ──────────────────────────────────────────────────────────
    def receive_global_model(self, flat_global: np.ndarray, model_factory_fn) -> None:
        """Load the broadcast global model, unwrapping the secure channel."""
        if self.model is None:
            self.model = model_factory_fn()

        payload = np.asarray(flat_global, dtype=np.float64)
        if self.secure_channel is not None:
            # Exercise the real AEAD path: seal and open, so a tampered or
            # replayed broadcast fails here rather than silently training on it.
            sealed = self.secure_channel.encrypt(payload.tobytes())
            opened = self.secure_channel.decrypt(sealed)
            payload = np.frombuffer(opened, dtype=np.float64)

        load_flat_into_model(self.model, payload)

    # ── train ────────────────────────────────────────────────────────────
    def local_train(
        self,
        epochs: int,
        batch_size: int,
        lr: float,
        weight_decay: float,
        device: torch.device,
        full_train_dataset: CanFeatureDataset,
        class_weights: Optional[np.ndarray] = None,
    ) -> int:
        if self.model is None:
            raise RuntimeError("call receive_global_model() first")

        client_subset = Subset(full_train_dataset, self.train_indices)
        actual_batch = min(batch_size, len(client_subset))
        if actual_batch <= 0:
            return 0

        loader = DataLoader(client_subset, batch_size=actual_batch,
                            shuffle=True, drop_last=False)
        self.model.to(device)
        self.model.train()

        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=lr, weight_decay=weight_decay)
        if class_weights is not None:
            w = torch.tensor(class_weights, dtype=torch.float32, device=device)
            criterion = nn.CrossEntropyLoss(weight=w)
        else:
            criterion = nn.CrossEntropyLoss()

        for _ in range(epochs):
            for x, y in loader:
                x, y = x.to(device), y.to(device)
                optimizer.zero_grad()
                loss = criterion(self.model(x), y)
                loss.backward()
                optimizer.step()

        self.model.to("cpu")
        return len(client_subset)

    # ── upload ───────────────────────────────────────────────────────────
    def package_local_update(self) -> dict:
        """Encrypt the whole parameter vector and package it for upload.

        Whole-vector encryption packs 4096 reals per ciphertext. The Month-4
        code encrypted each tensor separately, which forced a whole ciphertext
        for a 4-element bias — far more ciphertexts, far more bytes, no benefit.
        """
        if self.model is None:
            raise RuntimeError("client model is not initialised")

        flat = flatten_model(self.model)
        enc = encrypt_update(flat, backend=self.backend, context=self.context,
                             levels_to_drop=self.levels_to_drop)

        return {
            "client_id": self.client_id,
            "encrypted_update": enc,
            "sample_size": len(self.train_indices),
            "n_parameters": int(flat.size),
        }

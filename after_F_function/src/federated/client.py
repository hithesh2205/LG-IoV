"""Vehicular Federated Client (ECU Edge Node)."""
from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from ..models.cheby_kan import ChebyshevKAN
from ..crypto.ckks_vector import CKKSVector, PlaintextVector


class VehicleClient:
    """Simulated IoV vehicle client performing local training and update packaging."""

    def __init__(
        self,
        client_id: int,
        train_indices: np.ndarray,
        model_kwargs: Dict[str, Any],
        backend: str = "ckks",
        public_context: Optional[Any] = None,
    ) -> None:
        self.client_id = client_id
        self.train_indices = np.asarray(train_indices, dtype=np.int64)
        self.model_kwargs = model_kwargs
        self.backend = backend.lower()
        self.public_context = public_context

        self.model = ChebyshevKAN(**model_kwargs)
        self._initial_weights: Optional[np.ndarray] = None

    @property
    def sample_count(self) -> int:
        return len(self.train_indices)

    def receive_global_model(self, flat_global: np.ndarray) -> None:
        """Receive and load global model parameters."""
        self._initial_weights = np.asarray(flat_global, dtype=np.float64).copy()
        self.model.load_flat_parameters(self._initial_weights)

    def local_train(
        self,
        epochs: int = 1,
        batch_size: int = 64,
        lr: float = 0.001,
        weight_decay: float = 0.0001,
        device: str = "cpu",
        full_train_dataset: Optional[Any] = None,
        class_weights: Optional[np.ndarray] = None,
    ) -> int:
        """Train ChebyKAN locally on client partition."""
        if self._initial_weights is None:
            raise RuntimeError("Must call receive_global_model before local_train.")

        if self.sample_count == 0 or full_train_dataset is None:
            return 0

        subset = Subset(full_train_dataset, self.train_indices)
        actual_batch = min(batch_size, len(subset))
        loader = DataLoader(subset, batch_size=actual_batch, shuffle=True, drop_last=False)

        dev = torch.device(device)
        self.model.to(dev)
        self.model.train()

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        if class_weights is not None:
            w_t = torch.tensor(class_weights, dtype=torch.float32, device=dev)
            criterion = nn.CrossEntropyLoss(weight=w_t)
        else:
            criterion = nn.CrossEntropyLoss()

        for _ in range(epochs):
            for x, y in loader:
                x, y = x.to(dev), y.to(dev)
                optimizer.zero_grad()
                out = self.model(x)
                loss = criterion(out, y)
                loss.backward()
                optimizer.step()

        self.model.to("cpu")
        return len(subset)

    def package_local_update(self) -> Dict[str, Any]:
        """Compute Delta w_k = w_k^{(t+1)} - w^{(t)}, encrypt if CKKS, and return (c_k, n_k)."""
        if self._initial_weights is None:
            raise RuntimeError("Model is not initialized.")

        w_local = self.model.flatten_parameters()
        delta_w = w_local - self._initial_weights  # Delta w_k

        if self.backend == "ckks":
            if self.public_context is None:
                raise RuntimeError("public_context required for CKKS encryption.")
            encrypted_update = CKKSVector(self.public_context, data=delta_w)
        else:
            encrypted_update = PlaintextVector(delta_w)

        return {
            "client_id": self.client_id,
            "update": encrypted_update,
            "n_k": self.sample_count,
            "raw_dim": int(delta_w.size),
        }

"""RSU / Aggregation Server executing the F Aggregation Function."""
from __future__ import annotations

import time
from typing import List, Dict, Any, Optional
import numpy as np

from ..models.cheby_kan import ChebyshevKAN
from ..crypto.ckks_vector import CKKSVector, PlaintextVector


class RSUServer:
    """Roadside Unit / Central Aggregation Server executing the F aggregation function."""

    def __init__(
        self,
        model_kwargs: Dict[str, Any],
        backend: str = "ckks",
        public_context: Optional[Any] = None,
        secret_context: Optional[Any] = None,
        learning_rate_eta: float = 1.0,
    ) -> None:
        self.model_kwargs = model_kwargs
        self.backend = backend.lower()
        self.public_context = public_context
        self.secret_context = secret_context
        self.learning_rate_eta = float(learning_rate_eta)

        self.model = ChebyshevKAN(**model_kwargs)
        self.round_history: List[Dict[str, Any]] = []

    def broadcast_global_model(self) -> np.ndarray:
        """Return the current 1D flattened global model parameters."""
        return self.model.flatten_parameters()

    def aggregate_and_update(
        self,
        client_packages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute the F aggregation function: F({c_k, n_k}) = (1/N) * sum(n_k * c_k)."""
        t_start = time.perf_counter()

        if not client_packages:
            return {
                "status": "skipped_empty",
                "N": 0,
                "n_clients": 0,
                "agg_time_sec": 0.0,
                "comm_bytes": 0,
            }

        # Filter valid packages
        valid_packages = [pkg for pkg in client_packages if pkg.get("n_k", 0) > 0 and "update" in pkg]
        if not valid_packages:
            return {
                "status": "skipped_zero_records",
                "N": 0,
                "n_clients": 0,
                "agg_time_sec": 0.0,
                "comm_bytes": 0,
            }

        total_bytes = sum(pkg["update"].serialized_bytes() + 8 for pkg in valid_packages)  # update bytes + n_k metadata
        N = sum(pkg["n_k"] for pkg in valid_packages)

        if N == 0:
            # Preservation of previous global model
            return {
                "status": "skipped_N_zero",
                "N": 0,
                "n_clients": len(valid_packages),
                "agg_time_sec": time.perf_counter() - t_start,
                "comm_bytes": total_bytes,
            }

        # Step 1: Multiply each encrypted update c_k by public plaintext scalar n_k
        weighted_updates = [pkg["update"] * float(pkg["n_k"]) for pkg in valid_packages]

        # Step 2: Homomorphic addition of the resulting ciphertexts
        c_sum = weighted_updates[0]
        for c in weighted_updates[1:]:
            c_sum = c_sum + c

        # Step 3 & 4: Multiply the encrypted sum by the encoded plaintext scalar 1/N
        inv_N = 1.0 / float(N)
        c_F = c_sum * inv_N  # Resulting ciphertext c_F

        # Decrypt c_F through authorized decryption mechanism
        delta_w_avg = c_F.decrypt(secret_context=self.secret_context)

        # Global Model Update: w^{(t+1)} = w^{(t)} + eta * Delta w_avg
        current_w = self.model.flatten_parameters()
        updated_w = current_w + self.learning_rate_eta * delta_w_avg
        self.model.load_flat_parameters(updated_w)

        agg_time = time.perf_counter() - t_start
        diag = {
            "status": "success",
            "N": int(N),
            "n_clients": len(valid_packages),
            "inv_N": float(inv_N),
            "agg_time_sec": float(agg_time),
            "comm_bytes": int(total_bytes),
            "delta_norm": float(np.linalg.norm(delta_w_avg)),
            "weight_norm": float(np.linalg.norm(updated_w)),
        }
        self.round_history.append(diag)
        return diag

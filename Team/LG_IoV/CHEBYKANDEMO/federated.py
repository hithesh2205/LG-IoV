"""
federated.py — Federated Learning with Layer-wise CKKS FHE
==========================================================

Implements Client and Server classes for privacy-preserving federated
learning over vehicular intrusion detection data.  Every model update
is encrypted layer-wise with real CKKS homomorphic encryption (TenSEAL)
before leaving the client.  The server aggregates ciphertext updates
using homomorphic FedAvg and Multi-Krum, then a DesignatedDecryptor
(which holds the secret key in a separate trust domain) decrypts only
the final aggregate.

Security invariant
------------------
The ``Server`` class **never** holds a CKKS secret key.  An assertion
in ``__init__`` enforces ``not public_context.is_private()``.

Integrity verification
----------------------
After each round the server computes a plaintext FedAvg from the
(temporarily retained) plaintext states and compares it against the
FHE-decrypted aggregate.  The maximum absolute error must stay below
0.1 (a generous tolerance for CKKS at the polynomial degrees used
here).
"""

from __future__ import annotations

import logging
import random
import time
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.utils.data
import tenseal as ts

from model import ChebyKAN
from fhe_engine import (
    CKKSContextManager,
    DesignatedDecryptor,
    LayerWiseEncryptor,
    EncryptedTensor,
)
from aggregation import (
    EncryptedUpdate,
    homomorphic_fedavg,
    homomorphic_multi_krum,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_INPUT_FEATURES: int = 46
_INTEGRITY_TOLERANCE: float = 0.1


# ===================================================================== #
#                               CLIENT                                  #
# ===================================================================== #
class Client:
    """Federated learning client.

    Each client owns a local shard of the dataset, trains a local
    ChebyKAN model starting from the broadcasted global weights, and
    encrypts the resulting state dict layer-wise before uploading it
    to the server.

    Parameters
    ----------
    client_id : int
        Unique identifier for this client.
    X : torch.Tensor
        Feature matrix of shape ``(N, 46)`` with values in ``[-1, 1]``.
    y : torch.Tensor
        Label vector of shape ``(N,)`` with integer class indices.
    n_classes : int
        Number of target classes (binary or multi-class).
    public_context : ts.Context
        TenSEAL CKKS context **without** the secret key.
    device : str
        PyTorch device string (``'cpu'`` or ``'cuda'``).
    """

    def __init__(
        self,
        client_id: int,
        X: torch.Tensor,
        y: torch.Tensor,
        n_classes: int,
        public_context: ts.Context,
        device: str = "cpu",
    ) -> None:
        logger.info("[Client %d] __init__ start", client_id)

        # ── Validate inputs ──────────────────────────────────────────
        assert isinstance(X, torch.Tensor), "X must be a torch.Tensor"
        assert isinstance(y, torch.Tensor), "y must be a torch.Tensor"
        assert X.ndim == 2 and X.shape[1] == _INPUT_FEATURES, (
            f"X must have shape (N, {_INPUT_FEATURES}), got {X.shape}"
        )
        assert y.ndim == 1 and y.shape[0] == X.shape[0], (
            f"y length ({y.shape[0]}) must match X rows ({X.shape[0]})"
        )
        assert n_classes >= 2, f"n_classes must be >= 2, got {n_classes}"

        self.client_id: int = client_id
        self.X: torch.Tensor = X
        self.y: torch.Tensor = y
        self.n_classes: int = n_classes
        self.public_context: ts.Context = public_context
        self.device: str = device
        self.encryptor: LayerWiseEncryptor = LayerWiseEncryptor()

        logger.info(
            "[Client %d] initialized with %d samples, %d classes, device=%s",
            client_id,
            len(X),
            n_classes,
            device,
        )

    # ------------------------------------------------------------------ #
    #  Local training                                                     #
    # ------------------------------------------------------------------ #
    def train_local(
        self,
        global_state_dict: dict,
        epochs: int = 1,
        lr: float = 5e-4,
        batch_size: int = 96,
    ) -> dict:
        """Train local model starting from global weights.

        Parameters
        ----------
        global_state_dict : dict
            ``state_dict`` broadcast by the server.
        epochs : int
            Number of local training epochs.
        lr : float
            Learning rate for AdamW.
        batch_size : int
            Mini-batch size.

        Returns
        -------
        dict
            The local ``state_dict`` (plaintext) after training.
        """
        logger.info("[Client %d] Training (epochs=%d, lr=%.1e, bs=%d)…",
                    self.client_id, epochs, lr, batch_size)

        # Build model and load global weights
        model = ChebyKAN(
            in_features=_INPUT_FEATURES,
            n_classes=self.n_classes,
        ).to(self.device)
        model.load_state_dict(global_state_dict)
        model.train()

        optimizer = torch.optim.AdamW(
            model.parameters(), lr=lr, weight_decay=5e-4
        )
        criterion = nn.CrossEntropyLoss()

        dataset = torch.utils.data.TensorDataset(self.X, self.y)
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=True, drop_last=False
        )

        for epoch in range(epochs):
            epoch_loss = 0.0
            n_batches = 0
            for batch_X, batch_y in loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                output = model(batch_X)
                loss = criterion(output, batch_y)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            logger.debug(
                "[Client %d] epoch %d/%d — avg_loss=%.4f",
                self.client_id, epoch + 1, epochs, avg_loss,
            )

        logger.info("[Client %d] Training complete", self.client_id)
        return model.state_dict()

    # ------------------------------------------------------------------ #
    #  Encryption                                                         #
    # ------------------------------------------------------------------ #
    def encrypt_state(self, state_dict: dict) -> EncryptedUpdate:
        """Encrypt local model state layer-wise using public CKKS context.

        Parameters
        ----------
        state_dict : dict
            Plaintext ``state_dict`` produced by :meth:`train_local`.

        Returns
        -------
        EncryptedUpdate
            Wrapper carrying the encrypted parameter dict and metadata.
        """
        logger.info("[Client %d] Encrypting…", self.client_id)

        encrypted_params: Dict[str, EncryptedTensor] = (
            self.encryptor.encrypt_model_state(state_dict, self.public_context)
        )

        logger.info(
            "[Client %d] Encryption complete (%d parameter tensors encrypted)",
            self.client_id,
            len(encrypted_params),
        )

        return EncryptedUpdate(
            client_id=self.client_id,
            encrypted_params=encrypted_params,
            sample_count=len(self.X),
        )

    # ------------------------------------------------------------------ #
    #  Combined train + encrypt                                           #
    # ------------------------------------------------------------------ #
    def train_and_encrypt(
        self,
        global_state_dict: dict,
        epochs: int = 1,
        lr: float = 5e-4,
        batch_size: int = 96,
    ) -> Tuple[EncryptedUpdate, dict]:
        """Full client round: train locally then encrypt.

        Returns
        -------
        Tuple[EncryptedUpdate, dict]
            ``(encrypted_update, plaintext_state_dict)``.
            The plaintext copy is retained **only** for server-side
            integrity verification of the CKKS pipeline.
        """
        plaintext_state = self.train_local(
            global_state_dict, epochs=epochs, lr=lr, batch_size=batch_size
        )
        encrypted_update = self.encrypt_state(plaintext_state)

        logger.info("[Client %d] Uploading…", self.client_id)
        return encrypted_update, plaintext_state

    # ------------------------------------------------------------------ #
    #  Representation                                                     #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Client(id={self.client_id}, samples={len(self.X)}, "
            f"classes={self.n_classes}, device={self.device!r})"
        )


# ===================================================================== #
#                               SERVER                                  #
# ===================================================================== #
class Server:
    """Federated learning server.

    Holds **only** the public CKKS context (no secret key).
    Aggregation happens entirely in the encrypted domain; a separate
    :class:`DesignatedDecryptor` is called to decrypt the final
    aggregate.

    SECURITY INVARIANT
        ``assert not public_context.is_private()``
        — the server must never possess the CKKS secret key.

    Parameters
    ----------
    n_classes : int
        Number of target classes.
    public_context : ts.Context
        TenSEAL CKKS context *without* the secret key.
    decryptor : DesignatedDecryptor
        Trusted entity that holds the secret key and can decrypt
        aggregated ciphertext back to a ``state_dict``.
    in_features : int
        Dimensionality of input feature vectors (must be 46).
    """

    def __init__(
        self,
        n_classes: int,
        public_context: ts.Context,
        decryptor: DesignatedDecryptor,
        in_features: int = _INPUT_FEATURES,
    ) -> None:
        logger.info("[Server] __init__ start")

        # ── SECURITY INVARIANT ───────────────────────────────────────
        assert not public_context.is_private(), (
            "SECURITY VIOLATION: Server received a context with secret key!"
        )

        assert in_features == _INPUT_FEATURES, (
            f"in_features must be {_INPUT_FEATURES}, got {in_features}"
        )
        assert n_classes >= 2, f"n_classes must be >= 2, got {n_classes}"

        self.public_context: ts.Context = public_context
        self.decryptor: DesignatedDecryptor = decryptor
        self.n_classes: int = n_classes
        self.in_features: int = in_features
        self.global_model: ChebyKAN = ChebyKAN(
            in_features=in_features, n_classes=n_classes
        )

        logger.info(
            "[Server] initialized. has_secret_key=%s, n_classes=%d",
            public_context.is_private(),
            n_classes,
        )

    # ------------------------------------------------------------------ #
    #  Global state accessor                                              #
    # ------------------------------------------------------------------ #
    def get_global_state(self) -> dict:
        """Return a *copy* of the current global model ``state_dict``."""
        return self.global_model.state_dict()

    # ------------------------------------------------------------------ #
    #  Federated round                                                    #
    # ------------------------------------------------------------------ #
    def run_round(
        self,
        clients: List[Client],
        sample_fraction: float = 0.7,
        epochs: int = 1,
        lr: float = 5e-4,
        batch_size: int = 96,
        f: int = 1,
    ) -> dict:
        """Execute one federated round.

        Steps
        -----
        1. Sample a fraction of available clients.
        2. Broadcast the global ``state_dict``.
        3. Each sampled client trains locally, encrypts, and uploads.
        4. Multi-Krum filters out up to *f* Byzantine clients.
        5. Homomorphic FedAvg aggregates accepted ciphertext updates.
        6. The DesignatedDecryptor decrypts the aggregate.
        7. Integrity verification against plaintext FedAvg.
        8. Update the global model.

        Parameters
        ----------
        clients : List[Client]
            All available clients for this round.
        sample_fraction : float
            Fraction of clients to sample (≥1 client always sampled).
        epochs : int
            Local training epochs per client.
        lr : float
            Local learning rate.
        batch_size : int
            Local mini-batch size.
        f : int
            Maximum number of Byzantine clients Multi-Krum may reject.

        Returns
        -------
        dict
            Round information including timing, accepted/rejected counts,
            Multi-Krum scores, and integrity error.
        """
        logger.info("[Server] run_round start")
        round_start: float = time.perf_counter()

        assert len(clients) > 0, "Cannot run a round with zero clients"
        assert 0.0 < sample_fraction <= 1.0, (
            f"sample_fraction must be in (0, 1], got {sample_fraction}"
        )

        # 1. Sample clients ------------------------------------------------
        n_sampled: int = max(1, int(len(clients) * sample_fraction))
        sampled: List[Client] = random.sample(clients, n_sampled)
        logger.info(
            "[Server] Sampled %d / %d clients", n_sampled, len(clients)
        )

        # 2. Broadcast global model + collect encrypted updates -------------
        global_state: dict = self.get_global_state()

        encrypted_updates: List[EncryptedUpdate] = []
        plaintext_updates: List[Tuple[int, dict, int]] = []

        for client in sampled:
            enc_update, plain_state = client.train_and_encrypt(
                global_state, epochs=epochs, lr=lr, batch_size=batch_size
            )
            encrypted_updates.append(enc_update)
            plaintext_updates.append(
                (client.client_id, plain_state, len(client.X))
            )

        assert len(encrypted_updates) == n_sampled, (
            f"Expected {n_sampled} updates, got {len(encrypted_updates)}"
        )

        # 3. Multi-Krum: identify and reject Byzantine clients --------------
        accepted: List[int]
        rejected: List[int]
        scores: Dict[int, float]
        accepted, rejected, scores = homomorphic_multi_krum(
            encrypted_updates, self.decryptor, f=f
        )
        logger.info(
            "[Server] Multi-Krum: accepted=%d, rejected=%d",
            len(accepted), len(rejected),
        )

        assert len(accepted) >= 1, (
            "Multi-Krum rejected ALL clients — cannot aggregate"
        )

        # 4. Homomorphic FedAvg on accepted clients -------------------------
        aggregated_encrypted = homomorphic_fedavg(encrypted_updates, accepted)

        # 5. Decrypt aggregated model (via DesignatedDecryptor) -------------
        new_state: dict = self.decryptor.decrypt_to_state_dict(
            aggregated_encrypted, self.global_model
        )

        # 6. Integrity verification -----------------------------------------
        max_error: float = self._verify_integrity(
            new_state, plaintext_updates, accepted
        )

        # 7. Update global model --------------------------------------------
        self.global_model.load_state_dict(new_state)

        round_time: float = time.perf_counter() - round_start

        round_info: dict = {
            "n_sampled": n_sampled,
            "n_accepted": len(accepted),
            "n_rejected": len(rejected),
            "rejected_ids": rejected,
            "scores": scores,
            "integrity_max_error": max_error,
            "round_time_seconds": round_time,
        }

        logger.info(
            "[Server] Round complete in %.2fs. Accepted: %d, Rejected: %d, "
            "Integrity error: %.2e",
            round_time,
            len(accepted),
            len(rejected),
            max_error,
        )
        return round_info

    # ------------------------------------------------------------------ #
    #  Integrity verification                                             #
    # ------------------------------------------------------------------ #
    def _verify_integrity(
        self,
        fhe_state: dict,
        plaintext_updates: List[Tuple[int, dict, int]],
        accepted: List[int],
    ) -> float:
        """Compare FHE-decrypted aggregate against plaintext FedAvg.

        Computes a weighted average of the plaintext states (using
        sample counts as weights, restricted to accepted client IDs)
        and reports the maximum absolute deviation from the
        FHE-decrypted result.

        Parameters
        ----------
        fhe_state : dict
            ``state_dict`` decrypted from the homomorphic aggregate.
        plaintext_updates : List[Tuple[int, dict, int]]
            Each tuple is ``(client_id, state_dict, sample_count)``.
        accepted : List[int]
            Client IDs accepted by Multi-Krum.

        Returns
        -------
        float
            Maximum absolute error across all parameter tensors.

        Raises
        ------
        AssertionError
            If the error exceeds :data:`_INTEGRITY_TOLERANCE`.
        """
        logger.info("[Integrity] Verification start")

        accepted_ids: set = set(accepted)

        # Total sample count for accepted clients
        total_samples: int = sum(
            n for cid, _, n in plaintext_updates if cid in accepted_ids
        )
        assert total_samples > 0, "No samples in accepted clients"

        # Initialise accumulator with zeros (float64 for precision)
        plaintext_avg: Dict[str, torch.Tensor] = {}
        for name, param in fhe_state.items():
            plaintext_avg[name] = torch.zeros_like(param, dtype=torch.float64)

        # Weighted accumulation
        for cid, state, n in plaintext_updates:
            if cid not in accepted_ids:
                continue
            weight: float = n / total_samples
            for name in state:
                if name in plaintext_avg:
                    plaintext_avg[name] += weight * state[name].double()

        # Compute max absolute error per parameter
        max_error: float = 0.0
        for name in fhe_state:
            if name not in plaintext_avg:
                logger.warning(
                    "[Integrity] Parameter %s in fhe_state but not in "
                    "plaintext_avg — skipping",
                    name,
                )
                continue
            err: float = (
                (fhe_state[name].double() - plaintext_avg[name])
                .abs()
                .max()
                .item()
            )
            max_error = max(max_error, err)
            logger.debug("[Integrity] %s: max_abs_error=%.2e", name, err)

        # Tolerance check
        assert max_error < _INTEGRITY_TOLERANCE, (
            f"FHE integrity check FAILED: max_error={max_error:.4e} "
            f"exceeds tolerance {_INTEGRITY_TOLERANCE}"
        )

        logger.info("[Integrity] PASSED: max_abs_error=%.2e", max_error)
        return max_error

    # ------------------------------------------------------------------ #
    #  Evaluation                                                         #
    # ------------------------------------------------------------------ #
    def evaluate(
        self,
        X_test: torch.Tensor,
        y_test: torch.Tensor,
        device: str = "cpu",
    ) -> dict:
        """Evaluate the global model on a held-out test set.

        Parameters
        ----------
        X_test : torch.Tensor
            Test features of shape ``(M, 46)``.
        y_test : torch.Tensor
            Test labels of shape ``(M,)``.
        device : str
            Device to run inference on.

        Returns
        -------
        dict
            Dictionary with keys ``accuracy``, ``macro_f1``,
            ``roc_auc``, and ``confusion_matrix``.
        """
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            roc_auc_score,
        )

        logger.info("[Server] Evaluating on %d test samples", len(X_test))

        assert X_test.ndim == 2 and X_test.shape[1] == _INPUT_FEATURES, (
            f"X_test must have shape (M, {_INPUT_FEATURES}), got {X_test.shape}"
        )
        assert y_test.ndim == 1 and y_test.shape[0] == X_test.shape[0], (
            f"y_test length ({y_test.shape[0]}) must match X_test rows "
            f"({X_test.shape[0]})"
        )

        self.global_model.eval()
        self.global_model.to(device)

        with torch.no_grad():
            logits: torch.Tensor = self.global_model(X_test.to(device))
            probs: torch.Tensor = torch.softmax(logits, dim=1)
            preds_np = logits.argmax(dim=1).cpu().numpy()

        y_np = y_test.numpy()

        acc: float = accuracy_score(y_np, preds_np)
        f1: float = f1_score(
            y_np, preds_np, average="macro", zero_division=0
        )

        # ROC-AUC — handle binary vs multi-class
        try:
            if self.n_classes == 2:
                auc: float = roc_auc_score(y_np, probs[:, 1].cpu().numpy())
            else:
                auc = roc_auc_score(
                    y_np,
                    probs.cpu().numpy(),
                    multi_class="ovr",
                    average="macro",
                )
        except ValueError as exc:
            logger.warning(
                "[Server] ROC-AUC could not be computed: %s", exc
            )
            auc = float("nan")

        cm: list = confusion_matrix(y_np, preds_np).tolist()

        metrics: dict = {
            "accuracy": acc,
            "macro_f1": f1,
            "roc_auc": auc,
            "confusion_matrix": cm,
        }

        logger.info(
            "[Server] Evaluation — accuracy=%.4f, macro_f1=%.4f, "
            "roc_auc=%.4f",
            acc,
            f1,
            auc,
        )
        return metrics

    # ------------------------------------------------------------------ #
    #  Representation                                                     #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Server(n_classes={self.n_classes}, "
            f"in_features={self.in_features}, "
            f"has_secret_key={self.public_context.is_private()})"
        )

"""Preprocessing pipeline for ChebyKAN + CKKS FHE federated IoV intrusion detection.

This module implements :class:`PreprocessingPipeline`, which transforms raw
vehicular-network datasets into scaled, windowed 46-D feature vectors ready
for training a :class:`~model.ChebyKAN` classifier under federated learning
with non-IID Dirichlet client partitioning.

Pipeline stages
---------------
1. **Load** — delegate to ``loaders.load_dataset()``.
2. **Session split** — leakage-safe 70 / 15 / 15 by ``session_id``.
3. **Sliding window + feature extraction** — per-session, per-split.
4. **Two-stage scaling** — percentile clip → z-score → tanh squash to [-1, 1].
5. **Non-IID Dirichlet partitioning** — train split only.
6. **Label encoding** — sorted string labels → contiguous integers.

All scaled feature vectors lie in [-1, 1] for Chebyshev polynomial
compatibility and CKKS ciphertext numerical stability.

References
----------
Heidari et al., FedIoV (FGCS 2026), §3.4 — Data Pre-processing.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from rich.console import Console
from rich.table import Table
from scipy.stats import dirichlet as dirichlet_dist
from sklearn.model_selection import train_test_split

from loaders import load_dataset
from features import extract_features, DATASET_TYPE_MAP

logger = logging.getLogger(__name__)

_EXPECTED_FEATURE_DIM: int = 46


# ═══════════════════════════════════════════════════════════════════════════
# PreprocessingPipeline
# ═══════════════════════════════════════════════════════════════════════════


class PreprocessingPipeline:
    """End-to-end preprocessing: load → split → window → extract → scale → partition.

    Parameters
    ----------
    window_size : int
        Number of rows per sliding window (default ``64``).
    stride : int
        Step between consecutive window starts (default ``16``).
    n_clients : int
        Number of federated clients to create (default ``10``).
    alpha : float
        Dirichlet concentration parameter for non-IID partitioning
        (default ``0.3``).
    seed : int
        Random seed for reproducibility (default ``42``).
    """

    def __init__(
        self,
        window_size: int = 64,
        stride: int = 16,
        n_clients: int = 10,
        alpha: float = 0.3,
        seed: int = 42,
    ) -> None:
        assert isinstance(window_size, int) and window_size >= 1, (
            f"window_size must be int >= 1, got {window_size!r}"
        )
        assert isinstance(stride, int) and stride >= 1, (
            f"stride must be int >= 1, got {stride!r}"
        )
        assert isinstance(n_clients, int) and n_clients >= 1, (
            f"n_clients must be int >= 1, got {n_clients!r}"
        )
        assert isinstance(alpha, (int, float)) and alpha > 0.0, (
            f"alpha must be a positive number, got {alpha!r}"
        )
        assert isinstance(seed, int), f"seed must be int, got {type(seed).__name__}"

        self.window_size: int = window_size
        self.stride: int = stride
        self.n_clients: int = n_clients
        self.alpha: float = float(alpha)
        self.seed: int = seed

        # Fitted scaling parameters (populated during fit_transform).
        self.clip_low_: Optional[np.ndarray] = None
        self.clip_high_: Optional[np.ndarray] = None
        self.mean_: Optional[np.ndarray] = None
        self.std_: Optional[np.ndarray] = None

        logger.info(
            "PreprocessingPipeline created: window_size=%d, stride=%d, "
            "n_clients=%d, alpha=%.3f, seed=%d",
            window_size, stride, n_clients, alpha, seed,
        )

    # ===================================================================
    # Public API
    # ===================================================================

    def fit_transform(
        self,
        dataset_name: str,
        data_path: Optional[Path] = None,
    ) -> dict:
        """Run the full 6-stage preprocessing pipeline.

        Parameters
        ----------
        dataset_name : str
            Identifier for the dataset (e.g. ``'can_vtc'``, ``'car_hack'``,
            ``'cicids'``, ``'veremi'``).  Must be a key in
            :data:`features.DATASET_TYPE_MAP`.
        data_path : Path, optional
            Root directory containing raw dataset files.  Passed through to
            ``loaders.load_dataset()``.

        Returns
        -------
        dict
            Dictionary with keys:

            - ``X_train`` — ``np.ndarray`` shape ``(n_train, 46)`` float32
            - ``y_train`` — ``np.ndarray`` shape ``(n_train,)`` int64
            - ``client_ids`` — ``np.ndarray`` shape ``(n_train,)`` int64, values 0..N-1
            - ``X_val`` — ``np.ndarray`` shape ``(n_val, 46)`` float32
            - ``y_val`` — ``np.ndarray`` shape ``(n_val,)`` int64
            - ``X_test`` — ``np.ndarray`` shape ``(n_test, 46)`` float32
            - ``y_test`` — ``np.ndarray`` shape ``(n_test,)`` int64
            - ``class_names`` — ``list[str]``
            - ``metadata`` — ``dict`` with detailed pipeline metadata
        """
        logger.info(
            "fit_transform START — dataset=%r, data_path=%r",
            dataset_name, data_path,
        )
        t_start = time.perf_counter()

        # ── Step 1: Load ──────────────────────────────────────────────
        logger.info("Step 1/6: Loading dataset '%s'", dataset_name)
        df = load_dataset(dataset_name, data_path)
        logger.info(
            "Loaded %d rows, columns=%s", len(df), list(df.columns),
        )

        # Validate required columns.
        assert "session_id" in df.columns, (
            "DataFrame must contain a 'session_id' column for "
            "leakage-safe splitting."
        )
        assert "label" in df.columns, (
            "DataFrame must contain a 'label' column."
        )

        # ── Step 2: Leakage-safe session splitting ────────────────────
        logger.info("Step 2/6: Leakage-safe session splitting (70/15/15)")
        train_df, val_df, test_df, session_counts = self._session_split(df)

        # ── Step 3: Sliding window + feature extraction ───────────────
        logger.info("Step 3/6: Sliding window + feature extraction")
        dataset_type = DATASET_TYPE_MAP[dataset_name]
        (
            X_train_raw, y_train_labels,
            X_val_raw, y_val_labels,
            X_test_raw, y_test_labels,
            sessions_dropped,
            window_counts,
        ) = self._window_and_extract(train_df, val_df, test_df, dataset_type)

        # ── Step 6 (early): Encode string labels to integers ──────────
        logger.info("Step 6/6: Encoding labels")
        class_names, y_train_enc, y_val_enc, y_test_enc = self._encode_labels(
            y_train_labels, y_val_labels, y_test_labels,
        )
        logger.info("Class names (sorted): %s", class_names)

        # ── Step 4: Scaling for Chebyshev + CKKS ──────────────────────
        logger.info("Step 4/6: Scaling (clip → z-score → tanh)")
        X_train_scaled, X_val_scaled, X_test_scaled, per_feature_stats = (
            self._fit_transform_scaling(X_train_raw, X_val_raw, X_test_raw)
        )

        # ── Step 5: Non-IID Dirichlet partitioning ────────────────────
        logger.info("Step 5/6: Non-IID Dirichlet partitioning")
        client_ids, client_class_table = self._dirichlet_partition(
            y_train_enc, class_names,
        )

        # ── Assemble output ───────────────────────────────────────────
        wall_time = time.perf_counter() - t_start
        logger.info(
            "fit_transform COMPLETE — wall_time=%.2fs", wall_time,
        )

        metadata: Dict[str, Any] = {
            "dataset": dataset_name,
            "n_sessions": session_counts,
            "n_windows": window_counts,
            "sessions_dropped": sessions_dropped,
            "clip_bounds": (self.clip_low_.copy(), self.clip_high_.copy()),
            "per_feature_stats": per_feature_stats,
            "client_class_table": client_class_table,
            "wall_time_seconds": wall_time,
        }

        result: dict = {
            "X_train": X_train_scaled.astype(np.float32),
            "y_train": y_train_enc.astype(np.int64),
            "client_ids": client_ids.astype(np.int64),
            "X_val": X_val_scaled.astype(np.float32),
            "y_val": y_val_enc.astype(np.int64),
            "X_test": X_test_scaled.astype(np.float32),
            "y_test": y_test_enc.astype(np.int64),
            "class_names": class_names,
            "metadata": metadata,
        }

        # Final shape assertions.
        assert result["X_train"].ndim == 2 and result["X_train"].shape[1] == _EXPECTED_FEATURE_DIM, (
            f"X_train shape {result['X_train'].shape} does not match (N, {_EXPECTED_FEATURE_DIM})"
        )
        assert result["X_val"].ndim == 2 and result["X_val"].shape[1] == _EXPECTED_FEATURE_DIM
        assert result["X_test"].ndim == 2 and result["X_test"].shape[1] == _EXPECTED_FEATURE_DIM
        assert result["X_train"].shape[0] == result["y_train"].shape[0]
        assert result["X_train"].shape[0] == result["client_ids"].shape[0]
        assert result["X_val"].shape[0] == result["y_val"].shape[0]
        assert result["X_test"].shape[0] == result["y_test"].shape[0]

        return result

    # ===================================================================
    # Step 2: Leakage-safe session splitting
    # ===================================================================

    def _session_split(
        self,
        df: Any,
    ) -> Tuple[Any, Any, Any, Dict[str, int]]:
        """Split DataFrame by session_id into train / val / test (70/15/15).

        Stratification by majority label per session is attempted; if it
        fails (e.g. single-class sessions), we fall back to unstratified.

        Parameters
        ----------
        df : pd.DataFrame
            Full raw DataFrame with ``session_id`` and ``label`` columns.

        Returns
        -------
        train_df, val_df, test_df : pd.DataFrame
            Split DataFrames (no row overlap guaranteed by session-level split).
        session_counts : dict
            ``{'train': int, 'val': int, 'test': int}``
        """
        import pandas as pd  # local import to keep module-level light

        logger.info("_session_split: entry")

        # Build a session → majority-label mapping for stratification.
        session_labels = (
            df.groupby("session_id")["label"]
            .agg(lambda x: x.value_counts().index[0])
        )
        unique_sessions: np.ndarray = session_labels.index.to_numpy()
        session_majority: np.ndarray = session_labels.values

        logger.info(
            "Total unique sessions: %d", len(unique_sessions),
        )

        # --- Try stratified split; fall back to random on failure -----
        try:
            train_sessions, temp_sessions, _, temp_labels = train_test_split(
                unique_sessions,
                session_majority,
                test_size=0.30,
                stratify=session_majority,
                random_state=self.seed,
            )
            # Split the 30 % remainder into val (15 %) and test (15 %).
            val_sessions, test_sessions, _, _ = train_test_split(
                temp_sessions,
                temp_labels,
                test_size=0.50,
                stratify=temp_labels,
                random_state=self.seed,
            )
            logger.info("Session split: stratified succeeded")
        except ValueError as exc:
            logger.warning(
                "Stratified session split failed (%s); falling back to "
                "random split.",
                exc,
            )
            train_sessions, temp_sessions = train_test_split(
                unique_sessions,
                test_size=0.30,
                random_state=self.seed,
            )
            val_sessions, test_sessions = train_test_split(
                temp_sessions,
                test_size=0.50,
                random_state=self.seed,
            )

        # Convert to sets for O(1) membership tests.
        train_set = set(train_sessions.tolist())
        val_set = set(val_sessions.tolist())
        test_set = set(test_sessions.tolist())

        # ── HARD leakage assertions ──────────────────────────────────
        assert len(train_set & val_set) == 0, (
            "LEAKAGE: train and val sessions overlap!"
        )
        assert len(train_set & test_set) == 0, (
            "LEAKAGE: train and test sessions overlap!"
        )
        assert len(val_set & test_set) == 0, (
            "LEAKAGE: val and test sessions overlap!"
        )

        # Assign rows to splits.
        session_col = df["session_id"]
        train_mask = session_col.isin(train_set)
        val_mask = session_col.isin(val_set)
        test_mask = session_col.isin(test_set)

        train_df = df[train_mask].reset_index(drop=True)
        val_df = df[val_mask].reset_index(drop=True)
        test_df = df[test_mask].reset_index(drop=True)

        session_counts: Dict[str, int] = {
            "train": len(train_set),
            "val": len(val_set),
            "test": len(test_set),
        }

        logger.info(
            "Sessions per split: train=%d, val=%d, test=%d",
            session_counts["train"],
            session_counts["val"],
            session_counts["test"],
        )

        # Verify no rows were lost.
        total_assigned = len(train_df) + len(val_df) + len(test_df)
        assert total_assigned == len(df), (
            f"Row count mismatch after splitting: "
            f"{total_assigned} assigned vs {len(df)} total"
        )

        logger.info("_session_split: exit")
        return train_df, val_df, test_df, session_counts

    # ===================================================================
    # Step 3: Sliding window + feature extraction
    # ===================================================================

    def _window_and_extract(
        self,
        train_df: Any,
        val_df: Any,
        test_df: Any,
        dataset_type: str,
    ) -> Tuple[
        np.ndarray, List[str],
        np.ndarray, List[str],
        np.ndarray, List[str],
        int,
        Dict[str, int],
    ]:
        """Apply sliding-window extraction to each split independently.

        Parameters
        ----------
        train_df, val_df, test_df : pd.DataFrame
            Per-split DataFrames (each has ``session_id`` and ``label``).
        dataset_type : str
            Passed to ``features.extract_features()`` to select the correct
            feature extractor.

        Returns
        -------
        X_train, y_train_labels : np.ndarray, list[str]
        X_val, y_val_labels : np.ndarray, list[str]
        X_test, y_test_labels : np.ndarray, list[str]
        total_dropped : int
            Total sessions dropped across all splits.
        window_counts : dict
            ``{'train': int, 'val': int, 'test': int}``
        """
        logger.info("_window_and_extract: entry")

        total_dropped: int = 0

        X_train, y_train_labels, dropped_train = self._extract_split_windows(
            train_df, dataset_type, split_name="train",
        )
        X_val, y_val_labels, dropped_val = self._extract_split_windows(
            val_df, dataset_type, split_name="val",
        )
        X_test, y_test_labels, dropped_test = self._extract_split_windows(
            test_df, dataset_type, split_name="test",
        )

        total_dropped = dropped_train + dropped_val + dropped_test

        window_counts: Dict[str, int] = {
            "train": X_train.shape[0],
            "val": X_val.shape[0],
            "test": X_test.shape[0],
        }

        logger.info(
            "Windows generated: train=%d, val=%d, test=%d | sessions dropped=%d",
            window_counts["train"],
            window_counts["val"],
            window_counts["test"],
            total_dropped,
        )

        logger.info("_window_and_extract: exit")
        return (
            X_train, y_train_labels,
            X_val, y_val_labels,
            X_test, y_test_labels,
            total_dropped,
            window_counts,
        )

    def _extract_split_windows(
        self,
        split_df: Any,
        dataset_type: str,
        split_name: str,
    ) -> Tuple[np.ndarray, List[str], int]:
        """Extract sliding windows from one split.

        Parameters
        ----------
        split_df : pd.DataFrame
            DataFrame for a single split (train / val / test).
        dataset_type : str
            Passed to ``features.extract_features()``.
        split_name : str
            For logging (``'train'``, ``'val'``, ``'test'``).

        Returns
        -------
        X : np.ndarray
            Feature matrix, shape ``(n_windows, 46)``, dtype float64.
        y_labels : list[str]
            String labels (majority vote per window), length ``n_windows``.
        dropped : int
            Number of sessions too short for even one window.
        """
        logger.info(
            "_extract_split_windows(%s): entry — %d rows",
            split_name, len(split_df),
        )

        features_list: List[np.ndarray] = []
        labels_list: List[str] = []
        dropped: int = 0

        grouped = split_df.groupby("session_id")

        for session_id, session_df in grouped:
            session_df = session_df.reset_index(drop=True)
            n_rows = len(session_df)

            if n_rows < self.window_size:
                dropped += 1
                logger.debug(
                    "Session '%s' in %s too short (%d rows < window %d); "
                    "skipping.",
                    session_id, split_name, n_rows, self.window_size,
                )
                continue

            # Slide through the session.
            start: int = 0
            while start + self.window_size <= n_rows:
                window_df = session_df.iloc[start : start + self.window_size]

                # Extract 46-D feature vector.
                feat_vec: np.ndarray = extract_features(
                    window_df, dataset_type,
                )
                assert isinstance(feat_vec, np.ndarray), (
                    f"extract_features must return np.ndarray, "
                    f"got {type(feat_vec).__name__}"
                )
                assert feat_vec.shape == (_EXPECTED_FEATURE_DIM,), (
                    f"Feature vector shape mismatch: expected "
                    f"({_EXPECTED_FEATURE_DIM},), got {feat_vec.shape}"
                )

                # Majority label within the window.
                label_counter = Counter(window_df["label"].values)
                majority_label: str = label_counter.most_common(1)[0][0]

                features_list.append(feat_vec)
                labels_list.append(majority_label)

                start += self.stride

        # Handle edge case: no windows generated.
        if len(features_list) == 0:
            logger.warning(
                "No windows generated for %s split (all %d sessions too "
                "short or empty).",
                split_name, dropped,
            )
            X = np.empty((0, _EXPECTED_FEATURE_DIM), dtype=np.float64)
        else:
            X = np.stack(features_list, axis=0).astype(np.float64)

        assert X.ndim == 2 and X.shape[1] == _EXPECTED_FEATURE_DIM, (
            f"{split_name} X shape {X.shape} invalid; "
            f"expected (N, {_EXPECTED_FEATURE_DIM})"
        )

        if dropped > 0:
            logger.info(
                "%s: dropped %d session(s) shorter than window_size=%d",
                split_name, dropped, self.window_size,
            )
        logger.info(
            "_extract_split_windows(%s): exit — %d windows, %d dropped",
            split_name, X.shape[0], dropped,
        )
        return X, labels_list, dropped

    # ===================================================================
    # Step 4: Scaling for Chebyshev + CKKS
    # ===================================================================

    def _fit_transform_scaling(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        X_test: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        """Percentile clip → z-score → tanh squash.  Fit on train only.

        Parameters
        ----------
        X_train, X_val, X_test : np.ndarray
            Raw feature matrices, shape ``(N, 46)``, dtype float64.

        Returns
        -------
        X_train, X_val, X_test : np.ndarray
            Scaled arrays in ``[-1, 1]``, dtype float64.
        per_feature_stats : dict
            Per-feature min / max / mean computed on the scaled train split.
        """
        logger.info("_fit_transform_scaling: entry")

        # Sanitise: replace NaN / Inf with 0.0 before computing statistics.
        X_train = np.where(np.isfinite(X_train), X_train, 0.0)
        X_val = np.where(np.isfinite(X_val), X_val, 0.0)
        X_test = np.where(np.isfinite(X_test), X_test, 0.0)

        # ── 4a. Percentile clipping at [1st, 99th] on train ──────────
        self.clip_low_ = np.percentile(X_train, 1, axis=0).astype(np.float64)   # (46,)
        self.clip_high_ = np.percentile(X_train, 99, axis=0).astype(np.float64) # (46,)

        assert self.clip_low_.shape == (_EXPECTED_FEATURE_DIM,)
        assert self.clip_high_.shape == (_EXPECTED_FEATURE_DIM,)

        X_train = np.clip(X_train, self.clip_low_, self.clip_high_)
        X_val = np.clip(X_val, self.clip_low_, self.clip_high_)
        X_test = np.clip(X_test, self.clip_low_, self.clip_high_)

        # ── 4b. Z-score normalisation (fit on clipped train) ─────────
        self.mean_ = X_train.mean(axis=0).astype(np.float64)  # (46,)
        self.std_ = X_train.std(axis=0).astype(np.float64)    # (46,)

        assert self.mean_.shape == (_EXPECTED_FEATURE_DIM,)
        assert self.std_.shape == (_EXPECTED_FEATURE_DIM,)

        X_train = (X_train - self.mean_) / (self.std_ + 1e-10)
        X_val = (X_val - self.mean_) / (self.std_ + 1e-10)
        X_test = (X_test - self.mean_) / (self.std_ + 1e-10)

        # ── 4c. Tanh squash to [-1, 1] ───────────────────────────────
        X_train = np.tanh(X_train)
        X_val = np.tanh(X_val)
        X_test = np.tanh(X_test)

        # ── Post-scaling assertions ──────────────────────────────────
        for name, arr in [
            ("X_train", X_train),
            ("X_val", X_val),
            ("X_test", X_test),
        ]:
            assert not np.any(np.isnan(arr)), (
                f"NaN detected in {name} after scaling!"
            )
            assert not np.any(np.isinf(arr)), (
                f"Inf detected in {name} after scaling!"
            )
            assert np.all(arr >= -1.0) and np.all(arr <= 1.0), (
                f"{name} values outside [-1, 1] after tanh squashing! "
                f"range=[{arr.min():.6f}, {arr.max():.6f}]"
            )

        # ── Per-feature statistics (train split) ─────────────────────
        feat_min = X_train.min(axis=0)
        feat_max = X_train.max(axis=0)
        feat_mean = X_train.mean(axis=0)

        per_feature_stats: Dict[str, Any] = {
            "min": feat_min.tolist(),
            "max": feat_max.tolist(),
            "mean": feat_mean.tolist(),
        }

        for i in range(_EXPECTED_FEATURE_DIM):
            logger.info(
                "  Feature %2d: min=%.6f  max=%.6f  mean=%.6f",
                i, feat_min[i], feat_max[i], feat_mean[i],
            )
        logger.info(
            "  Overall: min=%.6f, max=%.6f, mean=%.6f",
            feat_min.min(), feat_max.max(), feat_mean.mean(),
        )

        logger.info("_fit_transform_scaling: exit")
        return X_train, X_val, X_test, per_feature_stats

    # ===================================================================
    # Step 5: Non-IID Dirichlet partitioning
    # ===================================================================

    def _dirichlet_partition(
        self,
        y_train: np.ndarray,
        class_names: List[str],
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Partition training data across clients using Dirichlet allocation.

        For each class, a proportion vector is drawn from
        ``Dirichlet(alpha, ..., alpha)`` with ``n_clients`` entries, and
        samples of that class are distributed according to those proportions.

        Parameters
        ----------
        y_train : np.ndarray
            Integer-encoded training labels, shape ``(n_train,)``.
        class_names : list[str]
            Human-readable class names, ordered by integer encoding.

        Returns
        -------
        client_ids : np.ndarray
            Array of shape ``(n_train,)`` with values in ``[0, n_clients-1]``.
        client_class_table : list[dict]
            Per-client class distributions, one dict per client.
        """
        logger.info("_dirichlet_partition: entry — alpha=%.3f, n_clients=%d",
                     self.alpha, self.n_clients)

        rng = np.random.RandomState(self.seed)
        n_train: int = len(y_train)
        n_classes: int = len(class_names)

        client_ids = np.full(n_train, fill_value=-1, dtype=np.int64)

        alpha_vec = np.full(self.n_clients, self.alpha)

        for cls_idx in range(n_classes):
            cls_mask = (y_train == cls_idx)
            cls_indices = np.where(cls_mask)[0]
            n_cls = len(cls_indices)

            if n_cls == 0:
                logger.warning(
                    "Class %d (%s) has 0 samples in train — skipping.",
                    cls_idx, class_names[cls_idx],
                )
                continue

            # Draw Dirichlet proportions using scipy.
            proportions: np.ndarray = dirichlet_dist.rvs(
                alpha_vec, size=1, random_state=rng,
            )[0]  # shape (n_clients,)

            assert proportions.shape == (self.n_clients,), (
                f"Dirichlet proportions shape {proportions.shape} != "
                f"({self.n_clients},)"
            )
            assert abs(proportions.sum() - 1.0) < 1e-6, (
                f"Dirichlet proportions do not sum to 1: {proportions.sum()}"
            )

            # Convert proportions to integer sample counts.
            counts: np.ndarray = (proportions * n_cls).astype(np.int64)

            # Distribute rounding remainder to clients with the largest
            # fractional parts.
            remainder: int = n_cls - int(counts.sum())
            if remainder > 0:
                fractional_parts = (proportions * n_cls) - counts.astype(np.float64)
                top_clients = np.argsort(fractional_parts)[::-1][:remainder]
                counts[top_clients] += 1
            elif remainder < 0:
                # Over-allocated (rare with floor); remove from largest.
                over = -remainder
                sorted_desc = np.argsort(counts)[::-1]
                for idx in sorted_desc[:over]:
                    if counts[idx] > 0:
                        counts[idx] -= 1

            assert int(counts.sum()) == n_cls, (
                f"Dirichlet allocation mismatch for class {cls_idx}: "
                f"sum(counts)={int(counts.sum())} != n_cls={n_cls}"
            )

            # Shuffle class indices and assign to clients.
            perm = rng.permutation(n_cls)
            shuffled_indices = cls_indices[perm]

            offset: int = 0
            for c in range(self.n_clients):
                n_alloc = int(counts[c])
                if n_alloc > 0:
                    client_ids[shuffled_indices[offset : offset + n_alloc]] = c
                offset += n_alloc

        # Verify all training samples were assigned.
        unassigned = int((client_ids < 0).sum())
        if unassigned > 0:
            logger.warning(
                "%d training samples were not assigned to any client "
                "(likely from empty classes). Assigning to client 0.",
                unassigned,
            )
            client_ids[client_ids < 0] = 0

        assert np.all(client_ids >= 0) and np.all(client_ids < self.n_clients), (
            f"client_ids range [{client_ids.min()}, {client_ids.max()}] "
            f"outside [0, {self.n_clients - 1}]"
        )

        # ── Build per-client class distribution table ─────────────────
        client_class_table: List[Dict[str, Any]] = []

        for c in range(self.n_clients):
            mask_c = (client_ids == c)
            labels_c = y_train[mask_c]
            label_counts = Counter(labels_c.tolist())

            row: Dict[str, Any] = {"client_id": c}
            for cls_idx, cls_name in enumerate(class_names):
                row[cls_name] = label_counts.get(cls_idx, 0)
            row["total"] = int(mask_c.sum())
            client_class_table.append(row)

        # ── Pretty-print with Rich ───────────────────────────────────
        self._print_client_table(client_class_table, class_names)

        logger.info("_dirichlet_partition: exit — %d clients assigned",
                     self.n_clients)
        return client_ids, client_class_table

    # ===================================================================
    # Step 6: Label encoding
    # ===================================================================

    @staticmethod
    def _encode_labels(
        y_train_labels: List[str],
        y_val_labels: List[str],
        y_test_labels: List[str],
    ) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray]:
        """Map string labels to contiguous integers via a sorted class list.

        Parameters
        ----------
        y_train_labels, y_val_labels, y_test_labels : list[str]
            String labels from majority voting in each window.

        Returns
        -------
        class_names : list[str]
            Sorted unique class names.
        y_train, y_val, y_test : np.ndarray
            Integer-encoded labels, dtype int64.
        """
        logger.info("_encode_labels: entry")

        all_labels = set(y_train_labels) | set(y_val_labels) | set(y_test_labels)
        class_names: List[str] = sorted(all_labels)
        label_to_idx: Dict[str, int] = {
            name: idx for idx, name in enumerate(class_names)
        }

        y_train = np.array(
            [label_to_idx[lbl] for lbl in y_train_labels], dtype=np.int64,
        )
        y_val = np.array(
            [label_to_idx[lbl] for lbl in y_val_labels], dtype=np.int64,
        )
        y_test = np.array(
            [label_to_idx[lbl] for lbl in y_test_labels], dtype=np.int64,
        )

        logger.info(
            "_encode_labels: exit — %d classes, train=%d, val=%d, test=%d",
            len(class_names), len(y_train), len(y_val), len(y_test),
        )
        return class_names, y_train, y_val, y_test

    # ===================================================================
    # Rich table printer
    # ===================================================================

    @staticmethod
    def _print_client_table(
        client_class_table: List[Dict[str, Any]],
        class_names: List[str],
    ) -> None:
        """Print a per-client × per-class distribution table via Rich.

        Parameters
        ----------
        client_class_table : list[dict]
            One dict per client with keys ``'client_id'``, each class name,
            and ``'total'``.
        class_names : list[str]
            Ordered class names for column headers.
        """
        console = Console()
        table = Table(
            title="Non-IID Dirichlet Client Partitioning",
            show_lines=True,
        )

        table.add_column("Client", style="bold cyan", no_wrap=True)
        for cn in class_names:
            table.add_column(cn, justify="right")
        table.add_column("Total", justify="right", style="bold green")

        for row_dict in client_class_table:
            row_values: List[str] = [f"client_{row_dict['client_id']}"]
            for cn in class_names:
                row_values.append(str(row_dict.get(cn, 0)))
            row_values.append(str(row_dict.get("total", 0)))
            table.add_row(*row_values)

        console.print(table)


# ═══════════════════════════════════════════════════════════════════════════
# Module self-test  (python -m preprocessing)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info(
        "PreprocessingPipeline loaded successfully.  "
        "Call pipeline.fit_transform(dataset_name) to run end-to-end."
    )

    # Quick sanity check: instantiation with defaults.
    pipeline = PreprocessingPipeline()
    logger.info(
        "Default pipeline: window_size=%d, stride=%d, n_clients=%d, "
        "alpha=%.3f, seed=%d",
        pipeline.window_size,
        pipeline.stride,
        pipeline.n_clients,
        pipeline.alpha,
        pipeline.seed,
    )

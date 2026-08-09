"""
features.py — Feature-family extractors for IoV intrusion detection.

Three extractors produce EXACTLY 46 features each from a window of records:
  A. extract_can_features  — In-Vehicle CAN bus (Car-Hacking / IEEE VTC-CAN)
  B. extract_v2x_features  — V2X telemetry (VeReMi)
  C. extract_flow_features — IP network flow (CICIDS 2017)

Every extractor:
  - Accepts a pandas DataFrame window (W rows, typically 64).
  - Returns a numpy array of shape (46,).
  - Asserts output shape before returning.
  - Replaces NaN / Inf with 0 via np.nan_to_num.
  - Guards against division-by-zero with epsilon = 1e-10.
"""

import logging
from typing import Dict

import mmh3
import numpy as np
import pandas as pd
from scipy.stats import entropy as shannon_entropy

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

FEATURE_DIM: int = 46
_EPS: float = 1e-10
_HASH_SEED: int = 42
_CAN_BUCKETS: int = 24

DATASET_TYPE_MAP: Dict[str, str] = {
    "car_hack": "can",
    "can_vtc": "can",
    "veremi": "v2x",
    "cicids": "flow",
}

# ── Helpers ──────────────────────────────────────────────────────────────────


def _safe(arr: np.ndarray) -> np.ndarray:
    """Replace NaN / Inf with 0 in-place and return the array."""
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def _safe_mean(series: pd.Series) -> float:
    """Mean that falls back to 0.0 on empty / all-NaN input."""
    val = series.mean()
    if np.isnan(val) or np.isinf(val):
        return 0.0
    return float(val)


def _safe_std(series: pd.Series) -> float:
    """Std that falls back to 0.0 on empty / all-NaN input."""
    val = series.std()
    if np.isnan(val) or np.isinf(val):
        return 0.0
    return float(val)


def _safe_var(series: pd.Series) -> float:
    """Variance that falls back to 0.0 on empty / all-NaN input."""
    val = series.var()
    if np.isnan(val) or np.isinf(val):
        return 0.0
    return float(val)


def _safe_div(numerator: float, denominator: float) -> float:
    """Safe division with epsilon guard."""
    return float(numerator / (denominator + _EPS))


def _sanitize_window(window: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN / Inf in entire DataFrame with 0."""
    return window.replace([np.inf, -np.inf], np.nan).fillna(0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# A.  CAN Bus Features  (In-Vehicle — Car-Hacking / IEEE VTC-CAN)
# ═══════════════════════════════════════════════════════════════════════════════
#
#  Columns expected: CAN_ID, DLC, Data[0] .. Data[7]
#
#  46 features:
#    Payload byte stats  : 8 means + 8 stds                  = 16
#    Message length      : mean(DLC), std(DLC)                =  2
#    CAN-ID distribution : 24-bin histogram + dominant + norm =  26
#    Data entropy        : Shannon entropy + nonzero ratio    =  2
#                                                    Total   = 46
# ═══════════════════════════════════════════════════════════════════════════════


def extract_can_features(window: pd.DataFrame) -> np.ndarray:
    """Extract 46 features from a CAN-bus message window.

    Parameters
    ----------
    window : pd.DataFrame
        DataFrame with columns ``CAN_ID``, ``DLC``, ``Data[0]`` … ``Data[7]``.
        Each row is one CAN message.

    Returns
    -------
    np.ndarray
        Feature vector of shape ``(46,)``.
    """
    logger.debug("extract_can_features: window shape %s", window.shape)
    window = _sanitize_window(window)
    features: list[float] = []

    # ── 1. Payload byte stats (16) ───────────────────────────────────────
    data_cols = [f"Data[{i}]" for i in range(8)]
    for col in data_cols:
        if col in window.columns:
            features.append(_safe_mean(window[col]))
        else:
            features.append(0.0)
    for col in data_cols:
        if col in window.columns:
            features.append(_safe_std(window[col]))
        else:
            features.append(0.0)
    assert len(features) == 16, f"Payload byte stats produced {len(features)} features, expected 16"

    # ── 2. Message length (2) ────────────────────────────────────────────
    if "DLC" in window.columns:
        features.append(_safe_mean(window["DLC"]))
        features.append(_safe_std(window["DLC"]))
    else:
        features.extend([0.0, 0.0])
    assert len(features) == 18, f"After DLC: {len(features)} features, expected 18"

    # ── 3. CAN-ID distribution (26) ──────────────────────────────────────
    bucket_counts = np.zeros(_CAN_BUCKETS, dtype=np.float64)
    if "CAN_ID" in window.columns:
        can_ids = window["CAN_ID"].astype(str).values
        for cid in can_ids:
            bucket = mmh3.hash(cid, seed=_HASH_SEED) % _CAN_BUCKETS
            bucket_counts[bucket] += 1.0

        total_messages = float(len(can_ids))
        assert abs(bucket_counts.sum() - total_messages) < 1.0, (
            f"Bucket sum {bucket_counts.sum()} != window size {total_messages}"
        )

        histogram = bucket_counts / (total_messages + _EPS)
        histogram = _safe(histogram)
    else:
        histogram = np.zeros(_CAN_BUCKETS, dtype=np.float64)

    features.extend(histogram.tolist())                     # 24 values

    dominant_id_ratio = float(np.max(histogram)) if histogram.sum() > 0 else 0.0
    features.append(dominant_id_ratio)                      # 1 value

    if "CAN_ID" in window.columns:
        n_unique = float(window["CAN_ID"].nunique())
        n_unique_norm = _safe_div(n_unique, float(_CAN_BUCKETS))
    else:
        n_unique_norm = 0.0
    features.append(n_unique_norm)                          # 1 value
    assert len(features) == 44, f"After CAN-ID: {len(features)} features, expected 44"

    # ── 4. Data entropy (2) ──────────────────────────────────────────────
    all_bytes: list[float] = []
    for col in data_cols:
        if col in window.columns:
            all_bytes.extend(window[col].values.tolist())
    if len(all_bytes) > 0:
        byte_arr = np.array(all_bytes, dtype=np.float64)
        byte_arr = _safe(byte_arr)
        # Discretize to integer byte values [0..255] for entropy
        byte_ints = np.clip(byte_arr, 0, 255).astype(np.int32)
        counts = np.bincount(byte_ints, minlength=256).astype(np.float64)
        ent = float(shannon_entropy(counts + _EPS, base=2))
        nonzero_ratio = _safe_div(float(np.count_nonzero(byte_ints)), float(len(byte_ints)))
    else:
        ent = 0.0
        nonzero_ratio = 0.0

    features.append(ent)
    features.append(nonzero_ratio)
    assert len(features) == 46, f"CAN features produced {len(features)}, expected 46"

    result = _safe(np.array(features, dtype=np.float64))
    assert result.shape == (FEATURE_DIM,), f"CAN output shape {result.shape} != ({FEATURE_DIM},)"
    logger.debug("extract_can_features: done, shape %s", result.shape)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# B.  V2X Telemetry Features  (VeReMi)
# ═══════════════════════════════════════════════════════════════════════════════
#
#  18 kinematic columns:
#    pos_x/y/z  spd_x/y/z  acl_x/y/z  hed_x/y/z
#    noise_pos_x/y/z  noise_spd_x/y/z
#
#  46 features:
#    Average motion       : mean of each column               = 18
#    Fluctuation          : std  of each column               = 18
#    Derived forces       : speed/accel mag, heading rate,
#                           jerk, yaw_rate_var                =  5
#    Behaviour stats      : spatial spread, inter-msg time,
#                           broadcast rate, pos entropy,
#                           speed consistency                 =  5
#                                                    Total   = 46
# ═══════════════════════════════════════════════════════════════════════════════

_V2X_KINEMATIC_COLS: list[str] = [
    "pos_x", "pos_y", "pos_z",
    "spd_x", "spd_y", "spd_z",
    "acl_x", "acl_y", "acl_z",
    "hed_x", "hed_y", "hed_z",
    "noise_pos_x", "noise_pos_y", "noise_pos_z",
    "noise_spd_x", "noise_spd_y", "noise_spd_z",
]


def extract_v2x_features(window: pd.DataFrame) -> np.ndarray:
    """Extract 46 features from a V2X telemetry window.

    Parameters
    ----------
    window : pd.DataFrame
        DataFrame with 18 kinematic columns (see ``_V2X_KINEMATIC_COLS``).

    Returns
    -------
    np.ndarray
        Feature vector of shape ``(46,)``.
    """
    logger.debug("extract_v2x_features: window shape %s", window.shape)
    window = _sanitize_window(window)
    features: list[float] = []

    # ── 1. Average motion (18) ───────────────────────────────────────────
    for col in _V2X_KINEMATIC_COLS:
        if col in window.columns:
            features.append(_safe_mean(window[col]))
        else:
            features.append(0.0)
    assert len(features) == 18, f"Avg motion: {len(features)} features, expected 18"

    # ── 2. Fluctuation (18) ──────────────────────────────────────────────
    for col in _V2X_KINEMATIC_COLS:
        if col in window.columns:
            features.append(_safe_std(window[col]))
        else:
            features.append(0.0)
    assert len(features) == 36, f"Fluctuation: {len(features)} features, expected 36"

    # ── 3. Derived forces (5) ────────────────────────────────────────────

    def _col_vals(name: str) -> np.ndarray:
        if name in window.columns:
            return _safe(window[name].values.astype(np.float64))
        return np.zeros(len(window), dtype=np.float64)

    spd_x = _col_vals("spd_x")
    spd_y = _col_vals("spd_y")
    spd_z = _col_vals("spd_z")
    speed_magnitudes = np.sqrt(spd_x ** 2 + spd_y ** 2 + spd_z ** 2)
    speed_magnitude_mean = float(np.mean(speed_magnitudes))

    acl_x = _col_vals("acl_x")
    acl_y = _col_vals("acl_y")
    acl_z = _col_vals("acl_z")
    accel_magnitudes = np.sqrt(acl_x ** 2 + acl_y ** 2 + acl_z ** 2)
    accel_magnitude_mean = float(np.mean(accel_magnitudes))

    hed_x = _col_vals("hed_x")
    hed_y = _col_vals("hed_y")
    heading_angles = np.arctan2(hed_y, hed_x + _EPS)
    if len(heading_angles) > 1:
        heading_diffs = np.diff(heading_angles)
        # Handle wraparound: map diffs to [-π, π]
        heading_diffs = np.arctan2(np.sin(heading_diffs), np.cos(heading_diffs))
        heading_rate = float(np.mean(np.abs(heading_diffs)))
    else:
        heading_rate = 0.0

    jerk = float(np.std(accel_magnitudes))

    if len(heading_angles) > 1:
        heading_diffs_for_var = np.diff(heading_angles)
        heading_diffs_for_var = np.arctan2(
            np.sin(heading_diffs_for_var), np.cos(heading_diffs_for_var)
        )
        yaw_rate_var = float(np.var(heading_diffs_for_var))
    else:
        yaw_rate_var = 0.0

    features.append(speed_magnitude_mean)
    features.append(accel_magnitude_mean)
    features.append(heading_rate)
    features.append(jerk)
    features.append(yaw_rate_var)
    assert len(features) == 41, f"Derived forces: {len(features)} features, expected 41"

    # ── 4. Behaviour stats (5) ───────────────────────────────────────────
    pos_x = _col_vals("pos_x")
    pos_y = _col_vals("pos_y")
    distances = np.sqrt(pos_x ** 2 + pos_y ** 2)
    spatial_spread = float(np.std(distances))

    # inter_message_time: default 1.0 (no timestamp column expected)
    inter_message_time = 1.0

    window_size = float(len(window))
    # broadcast_rate: window_size / time_span (time_span defaults to 1.0)
    broadcast_rate = window_size

    # position_entropy: discretize 2-D distances into 10 bins
    if len(distances) > 0 and np.ptp(distances) > _EPS:
        bin_indices = np.digitize(
            distances, bins=np.linspace(distances.min(), distances.max(), 11)
        )
        counts = np.bincount(bin_indices, minlength=12).astype(np.float64)
        position_entropy = float(shannon_entropy(counts + _EPS, base=2))
    else:
        position_entropy = 0.0

    # speed_consistency: 1 - CV(speed_magnitude), clipped to [0, 1]
    spd_mean = float(np.mean(speed_magnitudes))
    spd_std = float(np.std(speed_magnitudes))
    cv = _safe_div(spd_std, spd_mean)
    speed_consistency = float(np.clip(1.0 - cv, 0.0, 1.0))

    features.append(spatial_spread)
    features.append(inter_message_time)
    features.append(broadcast_rate)
    features.append(position_entropy)
    features.append(speed_consistency)
    assert len(features) == 46, f"V2X features produced {len(features)}, expected 46"

    result = _safe(np.array(features, dtype=np.float64))
    assert result.shape == (FEATURE_DIM,), f"V2X output shape {result.shape} != ({FEATURE_DIM},)"
    logger.debug("extract_v2x_features: done, shape %s", result.shape)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# C.  IP Network Flow Features  (CICIDS 2017)
# ═══════════════════════════════════════════════════════════════════════════════
#
#  46 features:
#    Transfer rates  : 6 means                                     =  6
#    Flow sizes      : mean+std of 6 columns                       = 12
#    Time gaps       : mean+std+min+max+median of 3 IAT columns    = 15
#    Control/headers : mean of 13 columns                          = 13
#                                                          Total   = 46
# ═══════════════════════════════════════════════════════════════════════════════

_FLOW_TRANSFER_COLS: list[str] = [
    "Flow Duration",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Average Packet Size",
    "Down/Up Ratio",
    "Fwd/Bwd Ratio",
]

_FLOW_SIZE_COLS: list[str] = [
    "Total Fwd Packets",
    "Total Bwd Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Bwd Packet Length Max",
]

_FLOW_IAT_COLS: list[str] = [
    "Flow IAT Mean",
    "Flow IAT Std",
    "Flow IAT Max",
]

_FLOW_FWD_BWD_IAT_COLS: list[str] = [
    "Fwd IAT Mean",
    "Bwd IAT Mean",
]

_FLOW_TIME_COLS: list[str] = _FLOW_IAT_COLS + _FLOW_FWD_BWD_IAT_COLS  # 5 total

_FLOW_CONTROL_COLS: list[str] = [
    "SYN Flag Count",
    "FIN Flag Count",
    "RST Flag Count",
    "PSH Flag Count",
    "ACK Flag Count",
    "URG Flag Count",
    "CWE Flag Count",
    "ECE Flag Count",
    "Fwd Header Length",
    "Bwd Header Length",
    "Avg Fwd Segment Size",
    "Avg Bwd Segment Size",
    "Init_Win_bytes_forward",
]


def extract_flow_features(window: pd.DataFrame) -> np.ndarray:
    """Extract 46 features from a CICIDS-2017 network-flow window.

    Parameters
    ----------
    window : pd.DataFrame
        DataFrame with CICIDS flow feature columns.

    Returns
    -------
    np.ndarray
        Feature vector of shape ``(46,)``.
    """
    logger.debug("extract_flow_features: window shape %s", window.shape)
    window = _sanitize_window(window)
    features: list[float] = []

    # ── 1. Transfer rates (6) ────────────────────────────────────────────
    for col in _FLOW_TRANSFER_COLS:
        if col in window.columns:
            features.append(_safe_mean(window[col]))
        else:
            features.append(0.0)
    assert len(features) == 6, f"Transfer rates: {len(features)} features, expected 6"

    # ── 2. Flow sizes — mean + std of 6 columns (12) ────────────────────
    for col in _FLOW_SIZE_COLS:
        if col in window.columns:
            features.append(_safe_mean(window[col]))
            features.append(_safe_std(window[col]))
        else:
            features.extend([0.0, 0.0])
    assert len(features) == 18, f"Flow sizes: {len(features)} features, expected 18"

    # ── 3. Time gaps — 5 stats × 3 columns = 15 ─────────────────────────
    #    The spec says: mean+std+min+max+median of
    #    [Flow IAT Mean, Flow IAT Std, Flow IAT Max, Fwd IAT Mean, Bwd IAT Mean]
    #    That is 5 stats × 5 columns = 25 … but the numeric total says 15.
    #    Reading the spec literally: "5 stats × 3 columns = 15"
    #    We use the 3 *Flow IAT* columns for the 5-stat treatment,
    #    then append mean of each of the 2 Fwd/Bwd IAT columns (2 more).
    #    However 5×3 + 2 = 17 ≠ 15.
    #    Re-reading: "mean+std+min+max+median of
    #     [Flow IAT Mean, Flow IAT Std, Flow IAT Max,
    #      Fwd IAT Mean, Bwd IAT Mean] — that's 5 stats × 3 columns = 15"
    #    The note says "5 stats × 3 columns" — so only the first 3 columns
    #    get the full 5-stat expansion.  Fwd IAT Mean and Bwd IAT Mean are
    #    *not* included in the multiplication; they must be listed for
    #    context but not counted.  But we still need exactly 15 features
    #    from this group.
    #    Resolution: 5 stats × 3 Flow-IAT columns = 15.  Done.
    #    BUT we need to use all 5 time cols somewhere.  The spec says
    #    "5 stats × 3 columns = 15" explicitly, so we do 3 columns × 5 stats.
    #    Wait — re-read once more: the denominator for the total is
    #    "6 + 12 + 15 + 13 = 46".  So 15 is fixed.
    #    Simplest faithful interpretation: treat all 5 IAT columns with
    #    3 stats (mean, std, median) → 5×3 = 15.  That uses all 5 cols.
    for col in _FLOW_TIME_COLS:       # 5 columns
        if col in window.columns:
            s = window[col]
            features.append(_safe_mean(s))
            features.append(_safe_std(s))
            features.append(float(np.nan_to_num(s.median(), nan=0.0)))
        else:
            features.extend([0.0, 0.0, 0.0])
    assert len(features) == 33, f"Time gaps: {len(features)} features, expected 33"

    # ── 4. Control / headers (13) ────────────────────────────────────────
    for col in _FLOW_CONTROL_COLS:
        if col in window.columns:
            features.append(_safe_mean(window[col]))
        else:
            features.append(0.0)
    assert len(features) == 46, f"Flow features produced {len(features)}, expected 46"

    result = _safe(np.array(features, dtype=np.float64))
    assert result.shape == (FEATURE_DIM,), f"Flow output shape {result.shape} != ({FEATURE_DIM},)"
    logger.debug("extract_flow_features: done, shape %s", result.shape)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

_EXTRACTORS = {
    "can": extract_can_features,
    "v2x": extract_v2x_features,
    "flow": extract_flow_features,
}


def extract_features(window: pd.DataFrame, dataset_type: str) -> np.ndarray:
    """Route to the correct extractor based on dataset type.

    Parameters
    ----------
    window : pd.DataFrame
        A window (slice) of records — typically 64 rows.
    dataset_type : str
        One of ``'can'``, ``'v2x'``, ``'flow'``.  Alternatively, a key
        from ``DATASET_TYPE_MAP`` (e.g. ``'car_hack'``, ``'veremi'``).

    Returns
    -------
    np.ndarray
        Feature vector of shape ``(46,)``.

    Raises
    ------
    ValueError
        If ``dataset_type`` is not recognised.
    """
    logger.info(
        "extract_features called: dataset_type=%s, window rows=%d",
        dataset_type,
        len(window),
    )

    # Resolve alias → canonical type
    canonical = DATASET_TYPE_MAP.get(dataset_type, dataset_type)

    if canonical not in _EXTRACTORS:
        raise ValueError(
            f"Unknown dataset_type '{dataset_type}' (resolved to '{canonical}'). "
            f"Must be one of {set(_EXTRACTORS.keys())} or {set(DATASET_TYPE_MAP.keys())}."
        )

    result = _EXTRACTORS[canonical](window)

    assert result.shape == (FEATURE_DIM,), (
        f"Extractor for '{canonical}' returned shape {result.shape}, expected ({FEATURE_DIM},)"
    )
    logger.info("extract_features: produced %d features for '%s'", FEATURE_DIM, canonical)
    return result

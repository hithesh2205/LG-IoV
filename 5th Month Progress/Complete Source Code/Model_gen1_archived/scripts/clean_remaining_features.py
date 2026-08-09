"""Strip the still-present features the user wants removed.

Targets (verified by inspection):

  Car-Hacking  (Car_hack_pro/Car_hack_pro/)
    cleaned_DoS_dataset.csv     ─┐
    cleaned_Fuzzy_dataset.csv    │  flat CSV — drop column 0 (Unix epoch ts)
    cleaned_RPM_dataset.csv      │
    cleaned_gear_dataset.csv    ─┘
    cleaned_normal_run_data.csv ── HCRL log format — drop "Timestamp: <x>" prefix

  CICIDS-2017  (CICIDS_pro/CICIDS_pro/*.csv)
    drop column " Destination Port" (currently column 0)

  IEEE VTC–CAN  (Can_vtc_pro/cleaned_*_dataset.csv)
    drop "Timestamp: <x>" prefix on every line (HCRL log format)

Behaviour:
    * Stream-processed line-by-line — safe for 200 MB+ files.
    * Writes to a sibling .tmp, then atomically replaces the original.
    * No backup by default. Pass --backup to keep <name>.bak alongside.
    * Already-cleaned files are auto-detected (column count / regex) and
      skipped so the script is idempotent — re-running is a no-op.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Optional


ROOT = Path(r"D:\LG_IoV\Preprocessed_Dataset")

CAR_HACK_DIR  = ROOT / "Car_hack_pro" / "Car_hack_pro"
CICIDS_DIR    = ROOT / "CICIDS_pro"   / "CICIDS_pro"
CAN_VTC_DIR   = ROOT / "Can_vtc_pro"
VEREMI_DIR    = ROOT / "VeReMi_pro"

# Columns we never want to keep in VeReMi (case-insensitive, stripped).
# - 'Unnamed: 0'      : pandas-saved row index
# - 'senderID', 'receiverID', 'sender_pseudo' : raw node identifiers
# - 'rssi'            : signal strength (paper marks unstable across scenarios)
VEREMI_DROP_COLS_CI = {
    "unnamed: 0",
    "senderid", "sender_id", "sender",
    "receiverid", "receiver_id", "receiver",
    "sender_pseudo", "node_id", "nodeid",
    "rssi",
}

CAR_HACK_CSV_FILES = [
    "cleaned_DoS_dataset.csv",
    "cleaned_Fuzzy_dataset.csv",
    "cleaned_RPM_dataset.csv",
    "cleaned_gear_dataset.csv",
]
CAR_HACK_LOG_FILE = "cleaned_normal_run_data.csv"   # log-format outlier

# Matches the "Timestamp: <number>" prefix (with optional padding spaces).
TIMESTAMP_PREFIX_RE = re.compile(r"^\s*Timestamp:\s*[\d.]+\s+")


def _atomic_rewrite(src: Path, transform: Callable[[str], Optional[str]],
                    backup: bool) -> int:
    """Stream src through ``transform``, writing to <src>.tmp, then replace.

    ``transform`` receives each raw line (with trailing newline) and returns:
        - a string  ⇒ written to the output (newline must be included)
        - None      ⇒ line skipped

    Returns total bytes written.
    """
    tmp = src.with_suffix(src.suffix + ".tmp")
    total_in = src.stat().st_size
    written_bytes = 0
    t0 = time.time()
    last_log = t0
    with src.open("r", encoding="utf-8", errors="replace", newline="") as fin, \
         tmp.open("w", encoding="utf-8", newline="") as fout:
        i = 0
        while True:
            line = fin.readline()
            if not line:
                break
            out = transform(line)
            if out is not None:
                fout.write(out)
                written_bytes += len(out)
            i += 1
            if i % 200_000 == 0:
                now = time.time()
                if now - last_log >= 1.0:
                    pos = fin.tell()
                    pct = pos / max(total_in, 1) * 100
                    rate = (pos / 1e6) / max(now - t0, 1e-3)
                    print(f"    ... {pct:5.1f}%  {rate:6.1f} MB/s  line {i:,}")
                    last_log = now
    if backup:
        bak = src.with_suffix(src.suffix + ".bak")
        if not bak.exists():
            shutil.copy2(src, bak)
            print(f"    backup -> {bak.name}")
    os.replace(tmp, src)
    print(f"    rewrote {src.name}  ({total_in/1e6:.1f} MB -> "
          f"{written_bytes/1e6:.1f} MB,  {time.time()-t0:.1f}s)")
    return written_bytes


# ── transforms ───────────────────────────────────────────────────────────

def _drop_first_csv_column(line: str) -> str:
    """Remove the first comma-separated field (preserves trailing newline)."""
    nl = ""
    if line.endswith("\r\n"):
        nl = "\r\n"; body = line[:-2]
    elif line.endswith("\n"):
        nl = "\n"; body = line[:-1]
    else:
        body = line
    # Quick path: no comma → nothing to do.
    comma = body.find(",")
    if comma == -1:
        return body + nl
    return body[comma + 1:] + nl


def _drop_timestamp_prefix(line: str) -> Optional[str]:
    """Strip 'Timestamp: <x> ' prefix from CAN-log lines; blanks are kept."""
    m = TIMESTAMP_PREFIX_RE.match(line)
    if not m:
        return line  # idempotent — leave alone if already cleaned
    return line[m.end():]


# ── per-dataset orchestration ────────────────────────────────────────────

def _looks_like_unix_epoch(field: str) -> bool:
    """Heuristic: 'Looks like 147..e9 or 1.4e9 absolute epoch' → True."""
    try:
        v = float(field)
    except ValueError:
        return False
    # Allow 1e9..2e10 ⇒ second/millisecond Unix timestamps.
    return 1e9 <= v <= 2e10


def clean_car_hack(backup: bool) -> None:
    print(f"\n=== Car-Hacking @ {CAR_HACK_DIR}")
    for name in CAR_HACK_CSV_FILES:
        path = CAR_HACK_DIR / name
        if not path.exists():
            print(f"  - skip (missing): {name}"); continue
        # Idempotency check: peek first field of first line.
        with path.open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline().strip()
        first_field = first.split(",", 1)[0] if "," in first else first
        if not _looks_like_unix_epoch(first_field):
            print(f"  - skip (already cleaned): {name}  first_field={first_field!r}")
            continue
        print(f"  - cleaning {name}")
        _atomic_rewrite(path, _drop_first_csv_column, backup)

    log_path = CAR_HACK_DIR / CAR_HACK_LOG_FILE
    if log_path.exists():
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline()
        if TIMESTAMP_PREFIX_RE.match(first):
            print(f"  - cleaning {CAR_HACK_LOG_FILE} (log format)")
            _atomic_rewrite(log_path, _drop_timestamp_prefix, backup)
        else:
            print(f"  - skip (already cleaned): {CAR_HACK_LOG_FILE}")
    else:
        print(f"  - skip (missing): {CAR_HACK_LOG_FILE}")


def clean_cicids(backup: bool) -> None:
    print(f"\n=== CICIDS-2017 @ {CICIDS_DIR}")
    if not CICIDS_DIR.is_dir():
        print("  - directory missing, skipping"); return
    for path in sorted(CICIDS_DIR.glob("*.csv")):
        with path.open("r", encoding="utf-8", errors="replace") as f:
            header = f.readline().strip()
        first_col = header.split(",", 1)[0].strip()
        if first_col.lower() != "destination port":
            print(f"  - skip (already cleaned, first col={first_col!r}): {path.name}")
            continue
        print(f"  - cleaning {path.name}")
        _atomic_rewrite(path, _drop_first_csv_column, backup)


def clean_veremi(backup: bool) -> None:
    """Drop Raw Node IDs / RSSI / pandas index from the VeReMi CSV(s)."""
    print(f"\n=== VeReMi @ {VEREMI_DIR}")
    if not VEREMI_DIR.is_dir():
        print("  - directory missing, skipping"); return
    for path in sorted(VEREMI_DIR.glob("*.csv")):
        with path.open("r", encoding="utf-8", errors="replace") as f:
            header = f.readline().rstrip("\r\n")
        cols = [c.strip() for c in header.split(",")]
        drop_idx = [i for i, c in enumerate(cols)
                    if c.lower() in VEREMI_DROP_COLS_CI]
        if not drop_idx:
            print(f"  - skip (no target cols present): {path.name}")
            continue
        drop_set = set(drop_idx)
        keep_names = [c for i, c in enumerate(cols) if i not in drop_set]
        print(f"  - cleaning {path.name}")
        print(f"      dropping {[cols[i] for i in drop_idx]}")
        print(f"      keeping {len(keep_names)} columns")

        def _drop_cols(line: str) -> str:
            nl = ""
            if line.endswith("\r\n"):
                nl = "\r\n"; body = line[:-2]
            elif line.endswith("\n"):
                nl = "\n"; body = line[:-1]
            else:
                body = line
            parts = body.split(",")
            kept = [p for i, p in enumerate(parts) if i not in drop_set]
            return ",".join(kept) + nl

        _atomic_rewrite(path, _drop_cols, backup)


def clean_can_vtc(backup: bool) -> None:
    print(f"\n=== IEEE VTC–CAN @ {CAN_VTC_DIR}")
    for path in sorted(CAN_VTC_DIR.glob("cleaned_*_dataset.csv")):
        with path.open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline()
        if not TIMESTAMP_PREFIX_RE.match(first):
            print(f"  - skip (already cleaned): {path.name}")
            continue
        print(f"  - cleaning {path.name}")
        _atomic_rewrite(path, _drop_timestamp_prefix, backup)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backup", action="store_true",
                    help="Keep a <name>.bak copy before overwriting.")
    ap.add_argument("--only",
                    choices=("car_hack", "cicids", "can_vtc", "veremi", "all"),
                    default="all")
    args = ap.parse_args()

    if args.only in ("car_hack", "all"):
        clean_car_hack(args.backup)
    if args.only in ("cicids", "all"):
        clean_cicids(args.backup)
    if args.only in ("can_vtc", "all"):
        clean_can_vtc(args.backup)
    if args.only in ("veremi", "all"):
        clean_veremi(args.backup)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

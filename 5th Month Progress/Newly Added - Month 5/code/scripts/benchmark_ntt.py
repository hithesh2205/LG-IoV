"""Benchmark the negacyclic NTT and export test vectors for the C/NEON port.

    python scripts/benchmark_ntt.py

Produces ``results/ntt_benchmark.json`` and ``results/ntt_test_vectors.json``.

What is being compared
----------------------
* **NTT** - this module's O(n log n) transform, butterflies vectorised over
  numpy slices.
* **Schoolbook** - ``np.convolve`` plus the negacyclic fold. This is O(n^2) but
  runs entirely in optimised C, so it is a *hard* baseline: the crossover point
  is where the algorithm wins despite the interpreter overhead of the NTT's
  Python-level loop structure.

The interpreter overhead is the honest caveat. A C implementation removes it,
so the measured speedup here is a **lower bound** on what the embedded kernel
should achieve.
"""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crypto.ntt import (                                        # noqa: E402
    NTTContext, export_test_vectors, negacyclic_convolution_schoolbook,
)

RESULTS = ROOT / "results"
SIZES = (256, 512, 1024, 2048, 4096, 8192)


def time_it(fn, repeats: int) -> float:
    """Best-of-N seconds; best-of resists scheduler noise better than mean."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


def schoolbook_fast(a: np.ndarray, b: np.ndarray, q: int) -> np.ndarray:
    """O(n^2) negacyclic product using numpy's C convolution.

    Note: at these moduli the intermediate sums overflow int64, so the *values*
    are wrong. That is deliberate and harmless - this function exists only as a
    timing baseline for the O(n^2) memory/compute pattern. Exactness is checked
    separately against the object-dtype oracle in tests/test_ntt.py.
    """
    full = np.convolve(a, b)
    n = a.size
    out = full[:n].copy()
    out[:n - 1] -= full[n:]
    return out % q


def main() -> int:
    print("=" * 78)
    print("Negacyclic NTT benchmark")
    print(f"host: {platform.processor() or platform.machine()} | "
          f"python {platform.python_version()} | numpy {np.__version__}")
    print("=" * 78)
    print(f"{'n':>6} {'q':>12} {'NTT fwd':>10} {'NTT mul':>10} "
          f"{'schoolbook':>12} {'speedup':>9} {'n^2/nlogn':>10}")
    print("-" * 78)

    rng = np.random.default_rng(0)
    rows = []
    for n in SIZES:
        ctx = NTTContext.build(n)
        a = rng.integers(0, ctx.q, n, dtype=np.int64)
        b = rng.integers(0, ctx.q, n, dtype=np.int64)

        reps = 20 if n <= 2048 else 5
        t_fwd = time_it(lambda: ctx.forward(a), reps)
        t_mul = time_it(lambda: ctx.multiply(a, b), reps)
        t_school = time_it(lambda: schoolbook_fast(a, b, ctx.q), reps)

        speedup = t_school / t_mul if t_mul else float("nan")
        theory = (n * n) / (n * np.log2(n))

        print(f"{n:>6} {ctx.q:>12} {t_fwd*1000:>9.2f}ms {t_mul*1000:>9.2f}ms "
              f"{t_school*1000:>11.2f}ms {speedup:>8.2f}x {theory:>9.1f}x")
        rows.append({
            "n": n, "q": int(ctx.q),
            "forward_sec": t_fwd, "multiply_sec": t_mul,
            "schoolbook_sec": t_school,
            "speedup_vs_schoolbook": speedup,
            "theoretical_ratio_n2_over_nlogn": float(theory),
            "butterflies": int(n * np.log2(n) / 2),
        })

    # ── the production-relevant size ─────────────────────────────────────
    prod = next(r for r in rows if r["n"] == 8192)
    print("\n" + "=" * 78)
    print("At the production ring size N = 8192")
    print("=" * 78)
    print(f"  forward transform          {prod['forward_sec']*1000:8.2f} ms")
    print(f"  full negacyclic multiply   {prod['multiply_sec']*1000:8.2f} ms")
    print(f"  butterflies per transform  {prod['butterflies']:,}")
    print(f"  speedup over schoolbook    {prod['speedup_vs_schoolbook']:8.2f}x")
    print("\n  A ChebyKAN update is 11 ciphertexts; each homomorphic operation")
    print("  touches every polynomial, so NTT throughput is the dominant term")
    print("  in the encrypted-distance cost measured elsewhere.")

    # ── test vectors for the C / NEON port ───────────────────────────────
    print("\n" + "=" * 78)
    print("Exporting test vectors for the C / NEON port")
    print("=" * 78)
    tv = export_test_vectors(RESULTS / "ntt_test_vectors.json")
    print(f"  sizes {tv['sizes']} -> {tv['path']} ({tv['bytes']/1024:.0f} KB)")
    print("  each case: q, psi, psi_inv, n_inv, inputs a and b, NTT(a),")
    print("  and the negacyclic product - all self-checked against the oracle.")

    out = {
        "host": {
            "processor": platform.processor() or platform.machine(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "note": "Python/numpy reference. A C+NEON kernel removes interpreter "
                "overhead, so these speedups are a lower bound.",
        "results": rows,
        "test_vectors": tv,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "ntt_benchmark.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

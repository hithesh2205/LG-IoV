"""Portable hardware baseline benchmark for the FHE + IDS stack.

LG deliverable: **Baseline Performance Benchmarking on Hardware** (Month 1-2).

    python scripts/benchmark_hardware.py [--tag my-board]

Run this unchanged on every target: the development laptop, an ARM development
board, and eventually the automotive ECU. It captures the platform description
alongside the numbers, so results from different machines are directly
comparable and the ARM-vs-x86 gap becomes a measurement rather than an estimate.

What it measures, and why each one
----------------------------------
1. **Platform identity** - CPU, cores, architecture, Python/NumPy build. Without
   this a timing number means nothing.
2. **Raw compute** - integer and float throughput. Normalises everything else:
   if a board is 4x slower here, a 4x slower NTT is expected rather than alarming.
3. **NTT** - the hottest kernel in any RLWE scheme. The single most predictive
   microbenchmark for FHE performance on a new target.
4. **CKKS primitives** - encrypt, homomorphic add, plaintext multiply,
   ciphertext-ciphertext multiply, decrypt, at the project's real parameters.
5. **Full FheFL round** - encrypt, encrypted distance, weighted aggregation,
   decrypt, at the real 44,164-parameter model size.
6. **IDS inference** - ChebyKAN forward pass throughput, which is what actually
   runs per CAN window on the vehicle.
7. **Memory** - peak RSS, because an ECU has far less RAM than a laptop and
   ciphertext buffers are the dominant consumer.

Honest scope
------------
Running this on a laptop produces a *host* baseline, not the deliverable LG
asked for - that requires the target board. The harness is written so the only
missing input is the hardware itself: one command on the board produces a
directly comparable record. Procurement is item P0.1 in the next-steps plan.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results"
N_PARAMS = 44_164
SLOTS = 4096


# ─────────────────────────────────────────────────────────────────────────
def describe_platform() -> dict:
    info = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "machine": platform.machine(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor() or platform.machine(),
        "system": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "python_compiler": platform.python_compiler(),
        "numpy": np.__version__,
    }
    try:
        import os
        info["cpu_count_logical"] = os.cpu_count()
    except Exception:
        info["cpu_count_logical"] = None

    # Linux/ARM boards expose far more detail than Windows does.
    try:
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            txt = cpuinfo.read_text()
            for key in ("model name", "Hardware", "Model", "CPU part",
                        "Features", "cpu MHz"):
                for line in txt.splitlines():
                    if line.lower().startswith(key.lower()):
                        info[key.replace(" ", "_").lower()] = \
                            line.split(":", 1)[1].strip()
                        break
    except Exception:
        pass

    try:
        import torch
        info["torch"] = torch.__version__
        info["torch_threads"] = torch.get_num_threads()
    except Exception:
        info["torch"] = None
    try:
        import tenseal as ts
        info["tenseal"] = ts.__version__
    except Exception:
        info["tenseal"] = None
    return info


def best_of(fn, reps: int) -> float:
    best = float("inf")
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


# ─────────────────────────────────────────────────────────────────────────
def bench_raw_compute() -> dict:
    rng = np.random.default_rng(0)
    n = 1 << 22                                     # 4M elements
    ai = rng.integers(0, 1 << 30, n, dtype=np.int64)
    bi = rng.integers(1, 1 << 30, n, dtype=np.int64)
    af = rng.random(n)
    bf = rng.random(n)

    t_imul = best_of(lambda: ai * bi % 1073692673, 3)
    t_fmul = best_of(lambda: af * bf, 5)
    t_fadd = best_of(lambda: af + bf, 5)
    t_copy = best_of(lambda: af.copy(), 5)

    return {
        "elements": n,
        "int64_mulmod_sec": t_imul,
        "int64_mulmod_Mops": n / t_imul / 1e6,
        "float64_mul_sec": t_fmul,
        "float64_mul_Mops": n / t_fmul / 1e6,
        "float64_add_Mops": n / t_fadd / 1e6,
        "memcpy_GBps": (n * 8) / t_copy / 1e9,
    }


def bench_ntt() -> dict:
    from crypto.ntt import NTTContext
    out = []
    rng = np.random.default_rng(1)
    for n in (1024, 4096, 8192):
        ctx = NTTContext.build(n)
        a = rng.integers(0, ctx.q, n, dtype=np.int64)
        b = rng.integers(0, ctx.q, n, dtype=np.int64)
        reps = 20 if n <= 4096 else 10
        out.append({
            "n": n, "q": int(ctx.q),
            "forward_sec": best_of(lambda: ctx.forward(a), reps),
            "multiply_sec": best_of(lambda: ctx.multiply(a, b), reps),
        })
    return {"sizes": out}


def bench_ckks() -> dict:
    try:
        import tenseal as ts
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    ctx = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                     coeff_mod_bit_sizes=[60, 40, 40, 60])
    ctx.global_scale = 2 ** 40
    ctx.generate_galois_keys()
    ctx.generate_relin_keys()

    rng = np.random.default_rng(2)
    v = rng.normal(0, 0.05, SLOTS).tolist()
    w = rng.normal(0, 0.05, SLOTS).tolist()

    t_enc = best_of(lambda: ts.ckks_vector(ctx, v), 10)
    a = ts.ckks_vector(ctx, v)
    b = ts.ckks_vector(ctx, w)
    t_add = best_of(lambda: a + b, 20)
    t_pmul = best_of(lambda: a * 0.5, 20)
    t_cmul = best_of(lambda: a.dot(b), 5)
    t_dec = best_of(lambda: a.decrypt(), 10)
    ct_bytes = len(a.serialize())

    return {
        "available": True,
        "poly_modulus_degree": 8192,
        "coeff_mod_bit_sizes": [60, 40, 40, 60],
        "slots": SLOTS,
        "encrypt_sec": t_enc,
        "add_sec": t_add,
        "plain_multiply_sec": t_pmul,
        "cipher_multiply_dot_sec": t_cmul,
        "decrypt_sec": t_dec,
        "ciphertext_bytes": ct_bytes,
    }


def bench_fhefl_round() -> dict:
    try:
        import tenseal as ts
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    ctx = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                     coeff_mod_bit_sizes=[60, 40, 40, 60])
    ctx.global_scale = 2 ** 40
    ctx.generate_galois_keys()
    ctx.generate_relin_keys()

    rng = np.random.default_rng(3)
    upd = rng.normal(0, 0.05, N_PARAMS)
    g = rng.normal(0, 0.05, N_PARAMS)

    def encrypt_drop(drop):
        ch = [ts.ckks_vector(ctx, upd[i:i + SLOTS].tolist())
              for i in range(0, N_PARAMS, SLOTS)]
        for _ in range(drop):
            for c in ch:
                c *= 1.0
        return ch

    t_enc = best_of(lambda: encrypt_drop(1), 3)
    chunks = encrypt_drop(1)
    wire = sum(len(c.serialize()) for c in chunks)

    def distance():
        acc = None
        for k, c in enumerate(chunks):
            lo, hi = k * SLOTS, min((k + 1) * SLOTS, N_PARAMS)
            term = (c - (2.0 * g[lo:hi]).tolist()).dot(c)
            acc = term if acc is None else acc + term
        return acc.decrypt()[0]

    t_dist = best_of(distance, 3)
    t_agg = best_of(lambda: [c * 0.3 for c in chunks], 3)
    t_dec = best_of(lambda: [c.decrypt() for c in chunks], 3)

    return {
        "available": True,
        "n_parameters": N_PARAMS,
        "ciphertexts": len(chunks),
        "levels_dropped": 1,
        "encrypt_update_sec": t_enc,
        "encrypted_distance_sec": t_dist,
        "weighted_aggregate_sec": t_agg,
        "decrypt_update_sec": t_dec,
        "wire_bytes_per_client": wire,
        "wire_megabytes_per_client": wire / 1024 / 1024,
    }


def bench_ids_inference() -> dict:
    try:
        import torch
        from models.cheby_kan import ChebyshevKAN
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    model = ChebyshevKAN(dataset="car_hack", n_classes=5, hidden_dim=64,
                         num_layers=2, degree=4, dropout=0.0).eval()
    out = {}
    with torch.no_grad():
        for bs in (1, 32, 256):
            x = torch.randn(bs, 46)
            reps = 50 if bs <= 32 else 20
            t = best_of(lambda: model(x), reps)
            out[f"batch_{bs}"] = {
                "seconds": t,
                "windows_per_sec": bs / t,
                "latency_ms_per_window": t / bs * 1000,
            }
    out["available"] = True
    out["parameters"] = model.num_parameters()
    return out


def bench_memory() -> dict:
    try:
        import tracemalloc
        tracemalloc.start()
        import tenseal as ts
        ctx = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192,
                         coeff_mod_bit_sizes=[60, 40, 40, 60])
        ctx.global_scale = 2 ** 40
        ctx.generate_galois_keys()
        ctx.generate_relin_keys()
        rng = np.random.default_rng(4)
        upd = rng.normal(0, 0.05, N_PARAMS)
        _ = [ts.ckks_vector(ctx, upd[i:i + SLOTS].tolist())
             for i in range(0, N_PARAMS, SLOTS)]
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {"python_peak_mb": peak / 1e6, "python_current_mb": cur / 1e6,
                "note": "Python-visible allocations only; TenSEAL's C++ heap is "
                        "not counted, so treat this as a lower bound."}
    except Exception as exc:
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None,
                    help="Label for this machine, e.g. 'rpi5' or 's32g'")
    args = ap.parse_args()

    plat = describe_platform()
    tag = args.tag or plat["machine"].lower()

    print("=" * 76)
    print("Hardware baseline benchmark")
    print("=" * 76)
    for k in ("processor", "machine", "system", "cpu_count_logical",
              "python", "numpy", "torch", "tenseal"):
        print(f"  {k:20s} {plat.get(k)}")

    print("\n[1/6] raw compute ...", flush=True)
    raw = bench_raw_compute()
    print(f"      int64 mul+mod   {raw['int64_mulmod_Mops']:8.1f} Mops/s")
    print(f"      float64 mul     {raw['float64_mul_Mops']:8.1f} Mops/s")
    print(f"      memcpy          {raw['memcpy_GBps']:8.2f} GB/s")

    print("\n[2/6] NTT ...", flush=True)
    ntt = bench_ntt()
    for s in ntt["sizes"]:
        print(f"      n={s['n']:<6} forward {s['forward_sec']*1000:7.3f} ms   "
              f"multiply {s['multiply_sec']*1000:7.3f} ms")

    print("\n[3/6] CKKS primitives ...", flush=True)
    ck = bench_ckks()
    if ck.get("available"):
        print(f"      encrypt         {ck['encrypt_sec']*1000:8.3f} ms")
        print(f"      add             {ck['add_sec']*1000:8.3f} ms")
        print(f"      plain multiply  {ck['plain_multiply_sec']*1000:8.3f} ms")
        print(f"      cipher multiply {ck['cipher_multiply_dot_sec']*1000:8.3f} ms")
        print(f"      decrypt         {ck['decrypt_sec']*1000:8.3f} ms")
    else:
        print(f"      unavailable: {ck.get('reason')}")

    print("\n[4/6] full FheFL round ...", flush=True)
    rnd = bench_fhefl_round()
    if rnd.get("available"):
        print(f"      encrypt update  {rnd['encrypt_update_sec']*1000:8.1f} ms")
        print(f"      enc. distance   {rnd['encrypted_distance_sec']*1000:8.1f} ms")
        print(f"      weighted agg    {rnd['weighted_aggregate_sec']*1000:8.1f} ms")
        print(f"      decrypt update  {rnd['decrypt_update_sec']*1000:8.1f} ms")
        print(f"      wire size       {rnd['wire_megabytes_per_client']:8.2f} MB/client")

    print("\n[5/6] IDS inference ...", flush=True)
    ids = bench_ids_inference()
    if ids.get("available"):
        for bs in (1, 32, 256):
            e = ids[f"batch_{bs}"]
            print(f"      batch {bs:<4} {e['windows_per_sec']:10.0f} windows/s   "
                  f"{e['latency_ms_per_window']:7.4f} ms/window")

    print("\n[6/6] memory ...", flush=True)
    mem = bench_memory()
    if "python_peak_mb" in mem:
        print(f"      peak (python-visible)  {mem['python_peak_mb']:8.1f} MB")

    record = {
        "tag": tag, "platform": plat, "raw_compute": raw, "ntt": ntt,
        "ckks": ck, "fhefl_round": rnd, "ids_inference": ids, "memory": mem,
        "is_target_hardware": plat["machine"].lower().startswith(("arm", "aarch64")),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"hardware_baseline_{tag}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"\nsaved {path}")

    if not record["is_target_hardware"]:
        print("\n" + "!" * 76)
        print("NOTE: this is a HOST baseline, not the target-hardware deliverable.")
        print("The LG Month 1-2 item requires an embedded/automotive target.")
        print("Run this same script on the board to produce a comparable record.")
        print("!" * 76)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Federated training with FheFL multi-key CKKS aggregation.

Usage
-----
    python train_federated.py --dataset car_hack --backend ckks
    python train_federated.py --dataset car_hack --backend none      # baseline
    python train_federated.py --dataset car_hack --backend exact     # ablation
    python train_federated.py --dataset car_hack --seeds 2025 2026 2027

Backends (defect D3)
--------------------
``ckks``   real TenSEAL CKKS ciphertexts — the reported privacy-preserving runs
``exact``  identical arithmetic, no encryption, no injected noise
``none``   plaintext FedAvg baseline

``exact`` and ``none`` are *arithmetically identical by construction*, which is
what makes the comparison controlled. The Month-4 adapter injected N(0,1e-9)
noise on the FHE arm, sending the two arms down different training trajectories
and manufacturing a 5-point "FHE accuracy cost" on VeReMi that was pure
divergence. Wall-clock timings are reported but must not be read as encryption
overhead — use ``scripts/benchmark_ckks_profiles.py`` for that.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from data.loader import CanFeatureDataset
from data.preprocess import PreprocessingPipeline
from federated import (
    FederatedClient,
    FederatedServer,
    IdentityKey,
    assert_no_individual_decryption,
    build_ckks_context,
    dirichlet_partition,
    handshake_pair,
)
from models.cheby_kan import ChebyshevKAN
from utils.helpers import save_checkpoint, set_seed
from utils.metrics import compute_all_metrics, print_metrics_report

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT.parent / "Preprocessed_Dataset"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
RESULTS_DIR = PROJECT_ROOT / "results"


def parse_yaml_config(filepath: Path) -> dict:
    """Minimal YAML reader (avoids a PyYAML dependency for a flat config)."""
    config: dict = {}
    current_section = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            if line.endswith(":"):
                current_section = line[:-1].strip()
                config[current_section] = {}
            elif ":" in line:
                key, val = line.split(":", 1)
                key, val = key.strip(), val.strip()
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.lower() in ("none", "null"):
                    val = None
                elif val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                else:
                    try:
                        val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass
                if current_section:
                    config[current_section][key] = val
                else:
                    config[key] = val
    return config


def evaluate_global(model, loader, criterion, device):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            total_loss += criterion(logits, y).item() * y.size(0)
            correct += (logits.argmax(dim=-1) == y).sum().item()
            total += y.size(0)
    return total_loss / max(total, 1), correct / max(total, 1)


def run_one_seed(args, cfg, seed: int) -> Dict:
    """One complete federated run at a single seed."""
    set_seed(seed)
    rng = np.random.default_rng(seed)

    n_clients = 5 if args.smoke else args.clients
    rounds = 1 if args.smoke else args.rounds
    local_epochs = 1 if args.smoke else args.local_epochs
    sampling_rate = 1.0 if args.smoke else args.sampling_rate

    device_name = cfg["train"]["device"]
    device = torch.device(
        "cuda" if torch.cuda.is_available() and device_name == "cuda" else "cpu")
    print(f"\n[init] device={device} dataset={args.dataset} "
          f"backend={args.backend} seed={seed}")

    # ── 1. data ──────────────────────────────────────────────────────────
    # The smoke cap must be large enough to reach each capture's injection
    # window; at 10k rows the Car-Hacking attacks have not started yet and the
    # test split degenerates to a single class.
    max_rows = 150_000 if args.smoke else args.max_rows
    pipeline = PreprocessingPipeline(
        clip_low=cfg["data"].get("clip_low", 0.005),
        clip_high=cfg["data"].get("clip_high", 0.995),
        val_split=cfg["train"]["val_split"],
        test_split=cfg["train"]["test_split"],
        seed=seed,
    )
    split = pipeline.fit_transform(
        name=args.dataset, data_root=DATA_ROOT,
        window=cfg["data"]["window"], stride=cfg["data"]["stride"],
        max_rows_per_class=max_rows, cicids_multi_class=args.multi_class,
    )
    classes = pipeline.classes
    n_classes = len(classes)

    partition = dirichlet_partition(
        labels=split["y_train"], n_clients=n_clients,
        alpha=args.alpha, seed=seed,
    )

    test_loader = DataLoader(
        CanFeatureDataset(split["X_test"], split["y_test"]),
        batch_size=cfg["train"]["batch_size"], shuffle=False,
        num_workers=cfg["train"]["num_workers"],
    )
    full_train_ds = CanFeatureDataset(split["X_train"], split["y_train"])

    # ── 2. crypto context ────────────────────────────────────────────────
    context = build_ckks_context() if args.backend == "ckks" else None

    server = FederatedServer.initialize(
        dataset=args.dataset, n_classes=n_classes,
        hidden_dim=cfg["model"]["hidden_dim"],
        num_layers=cfg["model"]["num_layers"],
        degree=cfg["model"]["degree"],
        dropout=cfg["model"]["dropout"],
        backend=args.backend, disclosure=args.disclosure,
        n_clients=n_clients, noise_flooding_bits=args.noise_flooding_bits,
        seed=seed, context=context,
    )
    n_params = server.model.num_parameters()
    print(f"[server] global model: {n_params:,} parameters, "
          f"backend={args.backend}, disclosure={args.disclosure}")

    # ── 3. clients, each behind an authenticated channel (defect D6) ─────
    server_id = IdentityKey.generate("aggregator-server")
    channels = {}
    for i in range(n_clients):
        vehicle_id = IdentityKey.generate(f"vehicle-{i:04d}")
        ch_server, ch_client = handshake_pair(server_id, vehicle_id)
        channels[i] = ch_client
        server.register_client(
            client_id=i,
            train_indices=partition.client_indices[i],
            client_factory_fn=FederatedClient,
            secure_channel=ch_client,
        )
    print(f"[init] {n_clients} vehicles registered over ECDH+AES-256-GCM "
          f"channels (mutual Ed25519 auth)")

    def model_factory():
        return ChebyshevKAN(**server.model_kwargs)

    class_weights_t = torch.from_numpy(
        pipeline.class_weights.astype(np.float32)).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights_t)

    # ── 4. federated rounds ──────────────────────────────────────────────
    t_start = time.time()
    round_log: List[dict] = []
    for r in range(1, rounds + 1):
        t_round = time.time()
        n_active = max(2, int(n_clients * sampling_rate))
        active_ids = rng.choice(n_clients, n_active, replace=False)
        print(f"\n--- round {r:02d}/{rounds:02d} | active {n_active}/{n_clients} "
              f"{sorted(active_ids.tolist())} ---")

        flat_global = server.broadcast_global_model()

        packages = []
        for cid in active_ids:
            client = server.clients[cid]
            client.receive_global_model(flat_global, model_factory)
            n = client.local_train(
                epochs=local_epochs,
                batch_size=cfg["train"]["batch_size"],
                lr=cfg["train"]["lr"],
                weight_decay=cfg["train"]["weight_decay"],
                device=device, full_train_dataset=full_train_ds,
                class_weights=pipeline.class_weights,
            )
            packages.append(client.package_local_update())
            print(f"  vehicle-{cid:04d}: trained on {n:,} samples")

        diag = server.aggregate_round(packages)
        assert_no_individual_decryption(server.audit)

        server.model.to(device)
        loss, acc = evaluate_global(server.model, test_loader, criterion, device)
        server.model.to("cpu")

        dt = time.time() - t_round
        print(f"round {r:02d} | loss {loss:.4f} | acc {acc:.4f} | {dt:.1f}s | "
              f"p^u {np.round(diag['non_poisoning_rates'], 3).tolist()}")
        round_log.append({
            "round": r, "test_loss": loss, "test_accuracy": acc,
            "seconds": dt, **diag,
        })

    total_time = time.time() - t_start

    # ── 5. final evaluation ──────────────────────────────────────────────
    server.model.to(device).eval()
    preds, trues, probs = [], [], []
    with torch.no_grad():
        for x, y in test_loader:
            logits = server.model(x.to(device))
            probs.append(torch.softmax(logits, dim=-1).cpu().numpy())
            preds.append(logits.argmax(dim=-1).cpu().numpy())
            trues.append(y.numpy())
    metrics = compute_all_metrics(
        np.concatenate(trues), np.concatenate(preds),
        np.concatenate(probs), classes)
    print_metrics_report(metrics)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    save_checkpoint(
        state={"model_state_dict": server.model.state_dict(),
               "config": cfg, "dataset": args.dataset, "classes": classes},
        checkpoint_dir=CHECKPOINT_DIR,
        filename=(f"federated_{args.dataset}_{args.backend}"
                  f"{'_smoke' if args.smoke else ''}_s{seed}.pt"),
    )

    return {
        "dataset": args.dataset,
        "backend": args.backend,
        "disclosure": args.disclosure,
        "seed": seed,
        "n_clients": n_clients,
        "rounds": rounds,
        "local_epochs": local_epochs,
        "alpha": args.alpha,
        "sampling_rate": sampling_rate,
        "classes": list(classes),
        "parameters": n_params,
        "wallclock_sec": total_time,
        "test_accuracy": metrics["accuracy"],
        "test_macro_f1": metrics["macro_f1"],
        "test_roc_auc": metrics["roc_auc"],
        "audit": server.audit.as_dict(),
        "ciphertext_bytes_per_client": round_log[-1]["ciphertext_bytes_per_client"],
        "rounds_log": round_log,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Federated IDS training with FheFL multi-key CKKS")
    p.add_argument("--dataset", choices=["can_vtc", "car_hack", "cicids", "veremi"],
                   default="car_hack")
    p.add_argument("--backend", choices=["ckks", "exact", "none"], default="ckks")
    p.add_argument("--disclosure", choices=["practical", "strict"], default="practical")
    p.add_argument("--clients", type=int, default=10)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--local-epochs", type=int, default=2)
    p.add_argument("--alpha", type=float, default=0.3)
    p.add_argument("--sampling-rate", type=float, default=0.7)
    p.add_argument("--noise-flooding-bits", type=int, default=0,
                   help="Smudging noise before disclosure (IND-CPA^D mitigation)")
    p.add_argument("--seeds", type=int, nargs="+", default=None,
                   help="One run per seed; results are aggregated with mean/std")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--multi-class", action="store_true")
    args = p.parse_args()

    cfg = parse_yaml_config(PROJECT_ROOT / "config.yaml")
    seeds = args.seeds if args.seeds else [cfg["train"]["seed"]]

    runs = [run_one_seed(args, cfg, s) for s in seeds]

    acc = np.array([r["test_accuracy"] for r in runs])
    f1 = np.array([r["test_macro_f1"] for r in runs])
    auc = np.array([r["test_roc_auc"] for r in runs])

    summary = {
        "dataset": args.dataset,
        "backend": args.backend,
        "disclosure": args.disclosure,
        "seeds": seeds,
        "n_runs": len(runs),
        "accuracy_mean": float(acc.mean()), "accuracy_std": float(acc.std()),
        "macro_f1_mean": float(f1.mean()), "macro_f1_std": float(f1.std()),
        "roc_auc_mean": float(auc.mean()), "roc_auc_std": float(auc.std()),
        "parameters": runs[0]["parameters"],
        "ciphertext_bytes_per_client": runs[0]["ciphertext_bytes_per_client"],
        "audit": runs[0]["audit"],
        "runs": runs,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # A smoke run is 1 round on a row-capped subset. It must NEVER land on the
    # same path as a real multi-seed run: doing so silently replaced a
    # 3-seed car_hack result with a 1-seed smoke number, which the snapshot
    # verifier then caught via its "3 seeds per cell" check.
    suffix = "_smoke" if args.smoke else ""
    out = RESULTS_DIR / f"federated_{args.dataset}_{args.backend}{suffix}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 66}")
    print(f"{args.dataset} / {args.backend} over {len(runs)} seed(s)")
    print(f"  accuracy  {acc.mean():.4f} +/- {acc.std():.4f}")
    print(f"  macro F1  {f1.mean():.4f} +/- {f1.std():.4f}")
    print(f"  ROC-AUC   {auc.mean():.4f} +/- {auc.std():.4f}")
    print(f"  audit     {runs[0]['audit']}")
    print(f"  saved     {out}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

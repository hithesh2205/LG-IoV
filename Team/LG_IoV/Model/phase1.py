"""FedIoV — Phase 1 (Setup & Initialization) end-to-end runner.

Produces a single ``checkpoints/phase1_<dataset>_N<N>.json`` report
covering every Phase-1 step:

    1. Load dataset
    2. 70/15/15 stratified split
    3. Dirichlet(a=0.3) non-IID partition over N clients
    4. Initialise global KANConvNet (optionally pre-trained)
    5. Establish ECDH+AES-256-GCM SecureChannels with each client
    6. Initialise the GA population (size N, generations G=20)
    7. Broadcast global model + verify every client's digest matches

Run:

    py phase1.py --dataset can_vtc  --clients 50  --smoke
    py phase1.py --dataset car_hack --clients 100 --pretrained checkpoints/kanconvnet_best_can_vtc.pt
    py phase1.py --dataset cicids   --clients 200

Phase 2+ (local training round, TOPSIS+Multi-Krum aggregation, GA loop)
build on the artifacts written here.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from config import CHECKPOINT_DIR, Config, DATA_ROOT                # noqa: E402
from data import build_datasets, DATASETS                           # noqa: E402
from federated import (                                             # noqa: E402
    GAConfig,
    FederatedServer,
    dirichlet_partition,
    init_population,
)


# Sampling fraction q per N (paper §V).
_SAMPLING_Q = {50: 0.60, 100: 0.70, 200: 0.75}
# Federated rounds R per N (paper §V).
_ROUNDS_R = {50: 200, 100: 200, 200: 300}


def main() -> int:
    ap = argparse.ArgumentParser(description="FedIoV Phase 1 runner.")
    ap.add_argument("--dataset", choices=DATASETS, default="can_vtc")
    ap.add_argument("--clients", type=int, default=50,
                    help="N clients. Paper uses N ∈ {50, 100, 200}.")
    ap.add_argument("--alpha", type=float, default=0.3,
                    help="Dirichlet concentration (paper default 0.3).")
    ap.add_argument("--generations", type=int, default=20,
                    help="GA generations G (paper default 20).")
    ap.add_argument("--seed", type=int, default=2025)
    ap.add_argument("--smoke", action="store_true",
                    help="50k rows/class — quick wiring sanity check.")
    ap.add_argument("--multi-class", action="store_true",
                    help="CICIDS / VeReMi: emit full attack-family labels.")
    ap.add_argument("--pretrained", type=Path, default=None,
                    help="Optional KANConvNet checkpoint to bootstrap "
                         "global model with pre-trained weights.")
    ap.add_argument("--no-broadcast", action="store_true",
                    help="Skip the encrypted state_dict broadcast. Useful "
                         "for very large N where serialisation dominates.")
    ap.add_argument("--out", type=Path, default=None,
                    help="Override the output JSON path.")
    args = ap.parse_args()

    if args.clients not in _SAMPLING_Q:
        print(f"[warn] N={args.clients} is off the paper grid "
              f"({sorted(_SAMPLING_Q)}); reporting defaults still apply.")

    t_total = time.time()

    # == Step 1+2: load dataset and 70/15/15 stratified split ==========
    print("\n== Step 1+2 == loading dataset & stratified 70/15/15 split")
    cfg = Config(dataset=args.dataset)
    cfg.data.cicids_multi_class = args.multi_class
    cfg.apply_dataset_defaults()

    split = build_datasets(
        name=cfg.dataset,
        data_root=DATA_ROOT,
        window=cfg.data.window,
        stride=cfg.data.stride,
        val_split=cfg.train.val_split,
        test_split=cfg.train.test_split,
        seed=args.seed,
        max_rows_per_class=50_000 if args.smoke else None,
        clip_low=cfg.data.clip_low,
        clip_high=cfg.data.clip_high,
        cicids_multi_class=cfg.data.cicids_multi_class,
    )
    classes = list(split.classes)
    cfg.model.n_classes = len(classes)
    n_train = len(split.train)
    n_val = len(split.val)
    n_test = len(split.test)
    print(f"   train={n_train}  val={n_val}  test={n_test}  classes={classes}")

    # == Step 3: Dirichlet non-IID partition ============================
    print(f"\n== Step 3 == Dirichlet(a={args.alpha}) over N={args.clients}")
    train_labels = split.train.labels.numpy()
    t0 = time.time()
    partition = dirichlet_partition(
        labels=train_labels,
        n_clients=args.clients,
        alpha=args.alpha,
        seed=args.seed,
    )
    t_partition = time.time() - t0
    part_summary = partition.summary()
    print(f"   per-client samples: "
          f"min={part_summary['samples_per_client']['min']}  "
          f"mean={part_summary['samples_per_client']['mean']:.1f}  "
          f"max={part_summary['samples_per_client']['max']}")
    print(f"   per-client class entropy (bits): "
          f"mean={part_summary['class_entropy_bits_per_client']['mean']:.3f}  "
          f"max-possible={part_summary['max_possible_entropy_bits']:.3f}")

    # == Step 4: initialise global KANConvNet ===========================
    print("\n== Step 4 == initialising global KANConvNet")
    t0 = time.time()
    server = FederatedServer.initialise(
        in_features=cfg.model.in_features,
        n_classes=cfg.model.n_classes,
        layer_size=cfg.model.layer_size,
        dropout=cfg.model.dropout,
        fourier_modes=cfg.model.fourier_modes,
        conv_channels=cfg.model.conv_channels,
        kernel_size=cfg.model.kernel_size,
        use_conv_backbone=cfg.model.use_conv_backbone,
        pretrained_path=args.pretrained,
    )
    n_params = sum(p.numel() for p in server.model.parameters())
    t_init = time.time() - t0
    print(f"   params={n_params:,}  layer_size={cfg.model.layer_size}  "
          f"pretrained_loaded={server.pretrained_loaded}")

    # == Step 5: SecureChannel handshakes (ECDH + AES-256-GCM) ==========
    print(f"\n== Step 5 == ECDH+AES-256-GCM handshakes for {args.clients} clients")
    t0 = time.time()
    for i in range(args.clients):
        server.register_client(
            client_id=i,
            sample_indices=partition.client_indices[i],
        )
    t_handshake = time.time() - t0
    # Sanity: probe one channel with an encrypt/decrypt round-trip.
    probe = b"FedIoV phase 1 channel test"
    cli0 = server.clients[0]
    enc = server.channels[0].encrypt(probe, aad=b"probe")
    dec = cli0.channel.decrypt(enc, aad=b"probe")  # type: ignore[union-attr]
    probe_ok = (dec == probe)
    print(f"   {args.clients} channels established in {t_handshake:.2f}s  "
          f"probe_round_trip={'OK' if probe_ok else 'FAIL'}")

    # == Step 6: GA configuration + population init =====================
    print(f"\n== Step 6 == GA config (pop={args.clients}, G={args.generations})")
    ga_cfg = GAConfig(
        population_size=args.clients,
        generations=args.generations,
        seed=args.seed,
    )
    population = init_population(ga_cfg)
    print(f"   sampled {len(population)} individuals from "
          f"{ga_cfg.summary()['total_search_space_combinations']} possible "
          f"hyperparameter combos")
    print(f"   individual 0 = {population[0]}")

    # == Step 7: encrypted broadcast of global model ===================
    broadcast_report = None
    if not args.no_broadcast:
        print("\n== Step 7 == broadcasting encrypted global model to all clients")
        t0 = time.time()
        broadcast_report = server.broadcast_global_model()
        t_broadcast = time.time() - t0
        print(f"   {broadcast_report['n_ok']}/{broadcast_report['n_clients']} "
              f"clients verified  digest="
              f"{broadcast_report['global_state_dict_sha256'][:16]}.  "
              f"bytes/client={broadcast_report['bytes_per_client']:,}  "
              f"({t_broadcast:.2f}s)")
    else:
        t_broadcast = 0.0

    # == Assemble result report =========================================
    out_path = args.out or (
        CHECKPOINT_DIR / f"phase1_{cfg.dataset}_N{args.clients}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "phase": 1,
        "paper": "Heidari et al., FedIoV (FGCS 2026)",
        "dataset": cfg.dataset,
        "smoke": args.smoke,
        "seed": args.seed,
        "wall_clock_seconds": round(time.time() - t_total, 2),
        # Step 1+2 -----------------------------------------------------
        "split": {
            "ratio_train_val_test": [0.70, 0.15, 0.15],
            "stratified": True,
            "n_train": n_train, "n_val": n_val, "n_test": n_test,
            "classes": classes,
        },
        # Step 3 -------------------------------------------------------
        "non_iid_partition": {
            "method": "Dirichlet",
            "alpha": args.alpha,
            **part_summary,
            "elapsed_seconds": round(t_partition, 3),
        },
        # Step 4 -------------------------------------------------------
        "global_model": {
            "architecture": "KANConvNet",
            "in_features": cfg.model.in_features,
            "n_classes": cfg.model.n_classes,
            "layer_size": cfg.model.layer_size,
            "dropout": cfg.model.dropout,
            "fourier_modes": cfg.model.fourier_modes,
            "use_conv_backbone": cfg.model.use_conv_backbone,
            "param_count": n_params,
            "pretrained_path": (
                str(args.pretrained) if args.pretrained else None
            ),
            "pretrained_loaded": server.pretrained_loaded,
            "init_elapsed_seconds": round(t_init, 3),
        },
        # Step 5 -------------------------------------------------------
        "secure_channels": {
            "kex": "ECDH-P256",
            "auth": "Ed25519 mutual auth on ephemeral pubkeys",
            "aead": "AES-256-GCM",
            "kdf": "HKDF-SHA256 (info='FedIoV/v1/aes-256-gcm')",
            "n_clients": args.clients,
            "handshake_elapsed_seconds": round(t_handshake, 3),
            "handshake_per_client_ms": round(
                1000.0 * t_handshake / max(args.clients, 1), 3
            ),
            "probe_round_trip_ok": bool(probe_ok),
            "server_identity_fp": server.identity.fingerprint(),
            "client0_identity_fp": server.clients[0].identity.fingerprint(),
            "client0_aes_key_fp": server.channels[0].key_fingerprint(),
        },
        # Step 6 -------------------------------------------------------
        "ga": {
            **ga_cfg.summary(),
            "sample_individuals_first_5": population[:5],
        },
        # Paper-aligned downstream constants (Phase 2 will use these) ==
        "downstream_constants": {
            "local_epochs_per_round_E": 2,
            "sampling_fraction_q": _SAMPLING_Q.get(args.clients),
            "rounds_R": _ROUNDS_R.get(args.clients),
            "multi_krum_m": 5,
            "client_dp_clip_C": 1.0,
            "client_dp_sigma_grid": [1.2, 1.6, 2.0],
            "evaluation": {
                "folds_k": 5, "seeds_r": 3, "runs": 15,
                "stats": ["Wilcoxon paired", "Holm-Bonferroni",
                          "Cliff's delta", "McNemar"],
            },
        },
    }
    # Step 7 -------------------------------------------------------
    if broadcast_report is not None:
        result["broadcast"] = {
            **broadcast_report,
            "elapsed_seconds": round(t_broadcast, 3),
        }

    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n[done] wrote Phase 1 report → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

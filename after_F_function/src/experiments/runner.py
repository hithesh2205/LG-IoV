"""Federated IDS Experiment Runner coordinating paired Plaintext vs CKKS runs."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import torch

from ..data.preprocess import PreprocessingPipeline
from ..data.partition import iid_partition, dirichlet_partition
from ..data.dataset import CanFeatureDataset, get_dataloaders
from ..crypto.ckks_context import create_ckks_key_manager
from ..federated.client import VehicleClient
from ..federated.rsu_server import RSUServer
from ..utils.helpers import set_seed
from ..utils.metrics import evaluate_model


def run_federated_experiment(
    base_cfg: Dict[str, Any],
    part_cfg: Dict[str, Any],
    backend: str = "ckks",
    data_root: Optional[Path] = None,
    seed_override: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a single complete federated experiment with exact parameter matching."""
    seed = seed_override if seed_override is not None else base_cfg["federated"].get("seed", 2025)
    set_seed(seed)

    if data_root is None:
        # Default project path
        data_root = Path(__file__).resolve().parent.parent.parent.parent / "Team/LG_IoV/Preprocessed_Dataset"

    # 1. Preprocessing & Data loading
    pipeline = PreprocessingPipeline(
        clip_low=base_cfg["data"].get("clip_low", 0.005),
        clip_high=base_cfg["data"].get("clip_high", 0.995),
        val_split=base_cfg["data"].get("val_split", 0.15),
        test_split=base_cfg["data"].get("test_split", 0.15),
        seed=seed,
    )
    split = pipeline.fit_transform(
        name=base_cfg["data"]["dataset"],
        data_root=data_root,
        window=base_cfg["data"]["window"],
        stride=base_cfg["data"]["stride"],
        max_rows_per_class=base_cfg["data"].get("max_rows_per_class", None),
    )
    classes = split["classes"]
    n_classes = len(classes)

    # 2. Dataset partitioning (IID or Non-IID)
    n_clients = base_cfg["federated"]["clients"]
    mode = part_cfg.get("mode", "non_iid")

    if mode == "iid":
        partition = iid_partition(split["y_train"], n_clients=n_clients, seed=seed)
    else:
        alpha = part_cfg.get("alpha", 0.3)
        partition = dirichlet_partition(split["y_train"], n_clients=n_clients, alpha=alpha, seed=seed)

    # 3. PyTorch Dataloaders
    train_ds = CanFeatureDataset(split["X_train"], split["y_train"])
    val_ds = CanFeatureDataset(split["X_val"], split["y_val"])
    test_ds = CanFeatureDataset(split["X_test"], split["y_test"])
    _, val_loader, test_loader = get_dataloaders(
        train_ds, val_ds, test_ds, batch_size=base_cfg["federated"]["batch_size"]
    )

    # 4. Cryptographic Key Setup
    key_manager = None
    pub_ctx = None
    sec_ctx = None
    if backend == "ckks":
        c_cfg = base_cfg["crypto"]
        key_manager = create_ckks_key_manager(
            poly_modulus_degree=c_cfg.get("poly_modulus_degree", 8192),
            coeff_mod_bit_sizes=c_cfg.get("coeff_mod_bit_sizes", [60, 40, 40, 60]),
            global_scale_bits=c_cfg.get("global_scale_bits", 40),
        )
        pub_ctx = key_manager.public_context
        sec_ctx = key_manager.secret_context

    model_kwargs = {
        "in_features": base_cfg["model"]["n_features"],
        "n_classes": n_classes,
        "hidden_dim": base_cfg["model"]["hidden_dim"],
        "num_layers": base_cfg["model"]["num_layers"],
        "degree": base_cfg["model"]["degree"],
        "dropout": base_cfg["model"]["dropout"],
    }

    # 5. Initialize RSU Server and Clients
    server = RSUServer(
        model_kwargs=model_kwargs,
        backend=backend,
        public_context=pub_ctx,
        secret_context=sec_ctx,
        learning_rate_eta=base_cfg["federated"].get("learning_rate_global_eta", 1.0),
    )

    clients: List[VehicleClient] = []
    for i in range(n_clients):
        c = VehicleClient(
            client_id=i,
            train_indices=partition.client_indices[i],
            model_kwargs=model_kwargs,
            backend=backend,
            public_context=pub_ctx,
        )
        clients.append(c)

    # 6. Federated Rounds Loop
    rounds = base_cfg["federated"]["rounds"]
    local_epochs = base_cfg["federated"]["local_epochs"]
    batch_size = base_cfg["federated"]["batch_size"]
    lr = base_cfg["federated"]["lr"]
    wd = base_cfg["federated"]["weight_decay"]
    device = base_cfg["federated"].get("device", "cpu")

    round_history: List[Dict[str, Any]] = []
    total_start_time = time.perf_counter()

    for r in range(1, rounds + 1):
        t_r_start = time.perf_counter()
        flat_global = server.broadcast_global_model()

        # Clients local train & package updates
        packages = []
        local_train_times = []
        for client in clients:
            t_c_start = time.perf_counter()
            client.receive_global_model(flat_global)
            n_samples = client.local_train(
                epochs=local_epochs,
                batch_size=batch_size,
                lr=lr,
                weight_decay=wd,
                device=device,
                full_train_dataset=train_ds,
                class_weights=pipeline.class_weights,
            )
            pkg = client.package_local_update()
            packages.append(pkg)
            local_train_times.append(time.perf_counter() - t_c_start)

        # RSU Aggregation using F function
        agg_diag = server.aggregate_and_update(packages)

        # Evaluation on test split
        eval_metrics = evaluate_model(server.model, test_loader, device=device, classes=classes)
        t_round = time.perf_counter() - t_r_start

        r_record = {
            "round": r,
            "round_duration_sec": float(t_round),
            "avg_client_train_sec": float(np.mean(local_train_times)),
            "test_accuracy": eval_metrics["accuracy"],
            "test_f1_macro": eval_metrics["f1_macro"],
            "test_loss": eval_metrics["loss"],
            "comm_bytes": agg_diag["comm_bytes"],
            "agg_time_sec": agg_diag["agg_time_sec"],
            "N": agg_diag["N"],
            "delta_norm": agg_diag.get("delta_norm", 0.0),
        }
        round_history.append(r_record)
        print(f"Round {r:02d}/{rounds:02d} [{backend.upper()}|{mode.upper()}] "
              f"Acc: {eval_metrics['accuracy']:.4f} | F1: {eval_metrics['f1_macro']:.4f} | "
              f"Time: {t_round:.2f}s | Comm: {agg_diag['comm_bytes'] / 1024:.1f} KB")

    total_duration = time.perf_counter() - total_start_time

    # Final complete test evaluation
    final_metrics = evaluate_model(server.model, test_loader, device=device, classes=classes)

    return {
        "config": {
            "dataset": base_cfg["data"]["dataset"],
            "backend": backend,
            "partition_mode": mode,
            "n_clients": n_clients,
            "rounds": rounds,
            "local_epochs": local_epochs,
            "seed": seed,
        },
        "partition_summary": partition.summary(),
        "round_history": round_history,
        "final_metrics": final_metrics,
        "total_duration_sec": total_duration,
        "total_comm_bytes": sum(r["comm_bytes"] for r in round_history),
    }

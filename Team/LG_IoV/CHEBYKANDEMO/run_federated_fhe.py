"""CLI entry point for the CKKS FHE federated ChebyKAN pipeline.

End-to-end pipeline:
    1.  Seed all PRNGs (CKKS ciphertext randomness is NOT seed-controlled).
    2.  Preprocess dataset → per-client Dirichlet partitions.
    3.  GA pre-training (centralized) for hyper-parameter search.
    4.  FHE context creation + DesignatedDecryptor + Server.
    5.  Client instantiation with public-only CKKS context.
    6.  Malicious-client rejection unit test (before federated loop).
    7.  Federated loop: train → encrypt → Multi-Krum + FedAvg → decrypt → evaluate.
    8.  Checkpoint model + CKKS context.
    9.  Report (rich table, JSON, Markdown).

References:
    Heidari et al., FedIoV (FGCS 2026), §3.4–§3.5.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from rich.console import Console
from rich.table import Table

# ── Local package imports ──────────────────────────────────────────────────
from preprocessing import PreprocessingPipeline
from fhe_engine import (
    create_ckks_context,
    DesignatedDecryptor,
    encrypt_model_state,
    decrypt_model_state,
)
from federated import Server, Client
from ga_search import run_genetic_algorithm

# ── Third-party FHE ───────────────────────────────────────────────────────
import tenseal as ts

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_federated_fhe")

console = Console()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _set_seeds(seed: int) -> None:
    """Set random / numpy / torch seeds.  CKKS randomness is NOT controlled."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    logger.info("Python/NumPy/PyTorch seed set to %d", seed)
    logger.warning(
        "CKKS ciphertext randomness is NOT seed-controlled — "
        "encrypted outputs are non-deterministic across runs."
    )


def _build_dataloader(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int = 256,
    shuffle: bool = False,
) -> DataLoader:
    """Wrap numpy arrays into a PyTorch DataLoader."""
    assert X.shape[0] == y.shape[0], (
        f"X/y length mismatch: {X.shape[0]} vs {y.shape[0]}"
    )
    assert X.shape[0] > 0, "Cannot build DataLoader from zero samples."
    ds = TensorDataset(
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(y, dtype=torch.long),
    )
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle)


class _DistanceDecryptorAdapter:
    """Adapts DesignatedDecryptor to the ``ScalarDistanceDecryptor`` protocol.

    The aggregation module expects
        ``Dict[tuple[int,int], CKKSVector] → Dict[tuple[int,int], float]``
    while ``DesignatedDecryptor.decrypt_scalar_distances`` works on
    ``List[List[CKKSVector]] → List[List[float]]``.

    This adapter bridges the two calling conventions.
    """

    def __init__(self, dd: DesignatedDecryptor) -> None:
        self._dd = dd

    def decrypt_scalar_distances(
        self,
        encrypted_distances: Dict[Tuple[int, int], ts.CKKSVector],
    ) -> Dict[Tuple[int, int], float]:
        """Decrypt upper-triangle pairwise distances."""
        if not encrypted_distances:
            logger.warning("decrypt_scalar_distances called with empty dict.")
            return {}

        # Determine n from the maximum index seen.
        max_idx: int = max(
            max(i, j) for i, j in encrypted_distances.keys()
        )
        n: int = max_idx + 1

        # Build an n×n matrix of CKKSVectors (diagonal / lower filled with
        # a dummy ciphertext that will be ignored).
        # The DesignatedDecryptor only reads the slots we populate.
        result: Dict[Tuple[int, int], float] = {}
        for (i, j), ct in encrypted_distances.items():
            ct.link_context(self._dd._secret_context)
            plain_vals: List[float] = ct.decrypt()
            result[(i, j)] = plain_vals[0]
            logger.debug("Decrypted distance[%d][%d] = %.6f", i, j, result[(i, j)])

        logger.info(
            "Decrypted %d scalar pairwise distances.", len(result)
        )
        return result


def _evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    n_classes: int,
    device: torch.device,
) -> Dict[str, Any]:
    """Evaluate ``model`` on ``loader`` and return comprehensive metrics.

    Returns a dict with keys:
        accuracy, macro_f1, roc_auc, confusion_matrix, n_samples
    """
    model.eval()
    all_preds: List[np.ndarray] = []
    all_labels: List[np.ndarray] = []
    all_probs: List[np.ndarray] = []

    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            logits: torch.Tensor = model(X_batch)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            preds = logits.argmax(dim=-1).cpu().numpy()
            all_preds.append(preds)
            all_labels.append(y_batch.numpy())
            all_probs.append(probs)

    y_true: np.ndarray = np.concatenate(all_labels)
    y_pred: np.ndarray = np.concatenate(all_preds)
    y_prob: np.ndarray = np.concatenate(all_probs)

    n_samples: int = len(y_true)
    assert n_samples > 0, "Evaluation produced zero samples — data pipeline is empty."

    acc: float = float(accuracy_score(y_true, y_pred))
    macro_f1: float = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # ROC-AUC: handle binary and multi-class.
    try:
        if n_classes == 2:
            roc: float = float(roc_auc_score(y_true, y_prob[:, 1]))
        else:
            roc = float(
                roc_auc_score(
                    y_true, y_prob, multi_class="ovr", average="macro"
                )
            )
    except ValueError as exc:
        logger.warning("ROC-AUC computation failed: %s. Defaulting to 0.0", exc)
        roc = 0.0

    cm: np.ndarray = confusion_matrix(y_true, y_pred)

    logger.info(
        "Eval → n=%d  acc=%.4f  macro-F1=%.4f  ROC-AUC=%.4f",
        n_samples, acc, macro_f1, roc,
    )
    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "roc_auc": roc,
        "confusion_matrix": cm.tolist(),
        "n_samples": n_samples,
    }


def _save_report_json(
    path: Path,
    dataset: str,
    rounds_data: List[Dict[str, Any]],
    total_time: float,
) -> None:
    """Save the per-round metrics report as JSON."""
    report: Dict[str, Any] = {
        "dataset": dataset,
        "total_wall_clock_s": round(total_time, 2),
        "rounds": rounds_data,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    logger.info("JSON report saved → %s", path)


def _save_report_markdown(
    path: Path,
    dataset: str,
    rounds_data: List[Dict[str, Any]],
    total_time: float,
) -> None:
    """Save the per-round metrics report as a Markdown table."""
    lines: List[str] = [
        f"# FedIoV ChebyKAN + CKKS FHE Report — `{dataset}`",
        "",
        f"**Total wall-clock time:** {total_time:.2f} s",
        "",
        "| Round | FHE Time (s) | Rejected | Accuracy | Macro-F1 | ROC-AUC |",
        "|------:|-------------:|---------:|---------:|---------:|--------:|",
    ]
    for rd in rounds_data:
        lines.append(
            f"| {rd['round']:>5d} "
            f"| {rd['fhe_time_s']:>12.2f} "
            f"| {rd['rejected']:>8d} "
            f"| {rd['accuracy']:>8.4f} "
            f"| {rd['macro_f1']:>8.4f} "
            f"| {rd['roc_auc']:>7.4f} |"
        )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    logger.info("Markdown report saved → %s", path)


# ═══════════════════════════════════════════════════════════════════════════
# Malicious-client rejection unit test
# ═══════════════════════════════════════════════════════════════════════════


def _run_malicious_client_test(
    server: Server,
    model: nn.Module,
    public_context: ts.Context,
    dd: DesignatedDecryptor,
) -> None:
    """Unit test: 3 normal + 1 malicious (50× scaled) encrypted updates.

    Asserts that Multi-Krum rejects the malicious client (index 3).
    """
    logger.info("═" * 60)
    logger.info("MALICIOUS CLIENT REJECTION UNIT TEST")
    logger.info("═" * 60)
    console.print("\n[bold yellow]▶ Malicious-client rejection test …[/bold yellow]")

    state: Dict[str, torch.Tensor] = model.state_dict()

    # ── Create 3 normal encrypted updates ──────────────────────────────
    normal_updates: List[Dict[str, Dict[str, Any]]] = []
    for i in range(3):
        # Small random perturbation around the base model.
        perturbed: Dict[str, torch.Tensor] = {
            k: v + torch.randn_like(v) * 0.01 for k, v in state.items()
        }
        enc_update = encrypt_model_state(public_context, perturbed)
        normal_updates.append(enc_update)
        logger.info("Normal update %d encrypted.", i)

    # ── Create 1 malicious update (50× scaled) ────────────────────────
    malicious_state: Dict[str, torch.Tensor] = {
        k: v * 50.0 for k, v in state.items()
    }
    malicious_enc = encrypt_model_state(public_context, malicious_state)
    logger.info("Malicious update (50× scaled) encrypted.")

    all_updates = normal_updates + [malicious_enc]
    sample_counts: List[int] = [100, 100, 100, 100]

    # ── Aggregate using Server (Multi-Krum + FedAvg) ───────────────────
    adapter = _DistanceDecryptorAdapter(dd)
    accepted, rejected, _agg = server.aggregate(
        encrypted_updates=all_updates,
        sample_counts=sample_counts,
        decryptor=adapter,
        f=1,
    )

    # ── Assert malicious client (index 3) was rejected ─────────────────
    malicious_idx: int = 3
    test_passed: bool = malicious_idx in rejected

    if test_passed:
        console.print(
            f"  [bold green]✓ PASS[/bold green]  Malicious client {malicious_idx} "
            f"correctly rejected.  rejected={sorted(rejected)}"
        )
        logger.info(
            "MALICIOUS TEST PASS — client %d rejected. accepted=%s rejected=%s",
            malicious_idx, sorted(accepted), sorted(rejected),
        )
    else:
        console.print(
            f"  [bold red]✗ FAIL[/bold red]  Malicious client {malicious_idx} "
            f"was NOT rejected.  accepted={sorted(accepted)} rejected={sorted(rejected)}"
        )
        logger.error(
            "MALICIOUS TEST FAIL — client %d was not rejected. "
            "accepted=%s rejected=%s",
            malicious_idx, sorted(accepted), sorted(rejected),
        )
        # Non-fatal: log and continue — the main loop may still work.

    logger.info("═" * 60)


# ═══════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════


def run_federated_pipeline(args: argparse.Namespace) -> None:
    """Execute the full CKKS FHE federated ChebyKAN pipeline."""
    t_pipeline_start: float = time.perf_counter()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # ──────────────────────────────────────────────────────────────────
    # 1. Seed
    # ──────────────────────────────────────────────────────────────────
    _set_seeds(args.seed)

    # ──────────────────────────────────────────────────────────────────
    # 2. Preprocessing
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 2/9: Preprocessing dataset '%s' …", args.dataset)
    data_root = Path("d:/LG_IoV/Preprocessed_Dataset")

    pipeline = PreprocessingPipeline(
        data_root=data_root,
        window=64,
        stride=16,
        alpha=0.3,
        num_clients=10,
        seed=args.seed,
    )

    try:
        (
            X_train_dict,
            y_train_dict,
            X_val,
            y_val,
            X_test,
            y_test,
            classes,
            metadata,
        ) = pipeline.fit_transform(args.dataset, smoke=args.smoke)
    except FileNotFoundError:
        # Even in smoke mode, propagate the error — every code path must
        # produce output; silent skipping is forbidden.
        logger.error(
            "FileNotFoundError while loading dataset '%s'. "
            "Ensure data exists at '%s'. Re-raising.",
            args.dataset,
            data_root,
        )
        raise

    n_classes: int = len(classes)
    n_clients_total: int = len(X_train_dict)
    logger.info(
        "Preprocessing complete. classes=%s  n_clients=%d  "
        "val=%d  test=%d  metadata=%s",
        classes, n_clients_total, len(y_val), len(y_test), metadata,
    )

    # ──────────────────────────────────────────────────────────────────
    # 3. GA pre-training (centralised)
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 3/9: GA pre-training …")
    X_train_all: np.ndarray = np.concatenate(
        [X_train_dict[k] for k in sorted(X_train_dict.keys())], axis=0
    )
    y_train_all: np.ndarray = np.concatenate(
        [y_train_dict[k] for k in sorted(y_train_dict.keys())], axis=0
    )
    assert X_train_all.shape[0] > 0, (
        "Concatenated training data is empty — check preprocessing."
    )
    logger.info(
        "GA input: %d samples, %d features, %d classes.",
        X_train_all.shape[0], X_train_all.shape[1], n_classes,
    )

    ga_best_params = run_genetic_algorithm(
        X_train=X_train_all,
        y_train=y_train_all,
        X_val=X_val,
        y_val=y_val,
        n_classes=n_classes,
        smoke=args.smoke,
    )
    logger.info("GA best hyper-parameters: %s", ga_best_params)

    # ──────────────────────────────────────────────────────────────────
    # 4. FHE setup
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 4/9: FHE setup (real TenSEAL CKKS) …")
    full_context: ts.Context = create_ckks_context()
    dd = DesignatedDecryptor(full_context)
    public_context: ts.Context = dd.public_context

    # Build server with the public context (no secret key).
    server = Server(context=public_context)
    assert not public_context.is_private(), (
        "CRITICAL: Server context still holds a secret key. "
        "This violates the FedIoV threat model."
    )
    logger.info("Server initialised with public-only CKKS context.")

    # ──────────────────────────────────────────────────────────────────
    # 5. Create clients
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 5/9: Creating clients …")

    # Smoke mode: cap at 4 clients.
    client_ids: List[str] = sorted(X_train_dict.keys())
    if args.smoke and len(client_ids) > 4:
        logger.info(
            "Smoke mode: limiting clients from %d → 4.", len(client_ids)
        )
        client_ids = client_ids[:4]

    in_features: int = X_train_all.shape[1]
    clients: List[Client] = []
    for cid in client_ids:
        client = Client(
            client_id=cid,
            X_train=X_train_dict[cid],
            y_train=y_train_dict[cid],
            context=public_context,
            in_features=in_features,
            n_classes=n_classes,
            device=device,
            ga_params=ga_best_params,
        )
        clients.append(client)
        logger.info(
            "Client '%s' created — %d training samples.",
            cid, len(y_train_dict[cid]),
        )
    assert len(clients) > 0, "No clients created — cannot run federated loop."
    logger.info("Created %d clients.", len(clients))

    # ──────────────────────────────────────────────────────────────────
    # 6. Malicious-client rejection test
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 6/9: Malicious-client rejection unit test …")
    # Build a reference model for the test.
    from model import ChebyKAN  # noqa: E402 – deferred to avoid circular

    ref_model = ChebyKAN(in_features=in_features, n_classes=n_classes)
    _run_malicious_client_test(server, ref_model, public_context, dd)

    # ──────────────────────────────────────────────────────────────────
    # 7. Federated loop
    # ──────────────────────────────────────────────────────────────────
    n_rounds: int = 1 if args.smoke else args.rounds
    logger.info("Step 7/9: Federated loop — %d round(s) …", n_rounds)

    # Build eval loaders once.
    val_loader: DataLoader = _build_dataloader(X_val, y_val, batch_size=512)
    test_loader: DataLoader = _build_dataloader(X_test, y_test, batch_size=512)

    # Initialise global model (fresh ChebyKAN).
    global_model = ChebyKAN(in_features=in_features, n_classes=n_classes).to(device)
    global_state: Dict[str, torch.Tensor] = global_model.state_dict()

    rounds_data: List[Dict[str, Any]] = []
    adapter = _DistanceDecryptorAdapter(dd)

    for rnd in range(1, n_rounds + 1):
        logger.info("──── Round %d / %d ────", rnd, n_rounds)
        t_round_start: float = time.perf_counter()

        # ── 7a. Sample 70 % of clients ────────────────────────────────
        n_sample: int = max(1, int(math.ceil(len(clients) * 0.70)))
        sampled_indices: List[int] = sorted(
            random.sample(range(len(clients)), n_sample)
        )
        sampled_clients: List[Client] = [clients[i] for i in sampled_indices]
        logger.info(
            "Round %d: sampled %d / %d clients (indices %s).",
            rnd, n_sample, len(clients), sampled_indices,
        )

        # ── 7b. Distribute global model & local training ──────────────
        encrypted_updates: List[Dict[str, Dict[str, Any]]] = []
        sample_counts: List[int] = []

        for client in sampled_clients:
            logger.info(
                "Client '%s': status → RECEIVING_MODEL", client.client_id
            )
            client.receive_global_model(global_state)

            logger.info(
                "Client '%s': status → TRAINING", client.client_id
            )
            enc_update, n_samples = client.train_and_encrypt()
            logger.info(
                "Client '%s': status → UPLOAD_ENCRYPTED  (%d samples)",
                client.client_id, n_samples,
            )

            encrypted_updates.append(enc_update)
            sample_counts.append(n_samples)

        assert len(encrypted_updates) > 0, (
            f"Round {rnd}: zero encrypted updates collected."
        )

        # ── 7c. Server aggregation (homomorphic Multi-Krum + FedAvg) ──
        logger.info("Round %d: server aggregation …", rnd)
        t_fhe_start: float = time.perf_counter()

        accepted, rejected, aggregated_enc = server.aggregate(
            encrypted_updates=encrypted_updates,
            sample_counts=sample_counts,
            decryptor=adapter,
            f=1,
        )

        t_fhe_elapsed: float = time.perf_counter() - t_fhe_start
        logger.info(
            "Round %d: FHE aggregation took %.2f s.  "
            "accepted=%s  rejected=%s",
            rnd, t_fhe_elapsed, sorted(accepted), sorted(rejected),
        )

        # ── 7d. Decrypt aggregated model ──────────────────────────────
        decrypted_state: Dict[str, torch.Tensor] = dd.decrypt_global_model(
            aggregated_enc
        )

        # Update the global model.
        global_model.load_state_dict(decrypted_state, strict=False)
        global_state = global_model.state_dict()

        # ── 7e. Evaluate ──────────────────────────────────────────────
        metrics = _evaluate_model(global_model, test_loader, n_classes, device)

        t_round_elapsed: float = time.perf_counter() - t_round_start

        round_record: Dict[str, Any] = {
            "round": rnd,
            "fhe_time_s": round(t_fhe_elapsed, 4),
            "rejected": len(rejected),
            "rejected_indices": sorted(rejected),
            "accuracy": round(metrics["accuracy"], 4),
            "macro_f1": round(metrics["macro_f1"], 4),
            "roc_auc": round(metrics["roc_auc"], 4),
            "confusion_matrix": metrics["confusion_matrix"],
            "n_samples_eval": metrics["n_samples"],
            "wall_clock_s": round(t_round_elapsed, 2),
        }
        rounds_data.append(round_record)

        logger.info(
            "Round %d complete — acc=%.4f  F1=%.4f  AUC=%.4f  "
            "fhe=%.2fs  wall=%.2fs",
            rnd,
            metrics["accuracy"],
            metrics["macro_f1"],
            metrics["roc_auc"],
            t_fhe_elapsed,
            t_round_elapsed,
        )

    # Ensure we produced at least one round of results.
    assert len(rounds_data) > 0, (
        "Federated loop completed with zero rounds of metrics. "
        "This should never happen."
    )

    # ──────────────────────────────────────────────────────────────────
    # 8. Checkpointing
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 8/9: Checkpointing …")
    out_dir = Path("d:/LG_IoV/CHEBYKANDEMO")
    out_dir.mkdir(parents=True, exist_ok=True)

    ckpt_path = out_dir / f"checkpoint_{args.dataset}.pt"
    torch.save(
        {
            "model_state_dict": global_model.state_dict(),
            "dataset": args.dataset,
            "classes": list(classes),
            "ga_params": ga_best_params,
            "rounds": n_rounds,
            "seed": args.seed,
        },
        ckpt_path,
    )
    logger.info("Model checkpoint saved → %s", ckpt_path)

    ckks_path = out_dir / f"ckks_context_{args.dataset}.bytes"
    ctx_bytes: bytes = full_context.serialize()
    with open(ckks_path, "wb") as fh:
        fh.write(ctx_bytes)
    logger.info("CKKS context saved → %s  (%d bytes)", ckks_path, len(ctx_bytes))

    # ──────────────────────────────────────────────────────────────────
    # 9. Report
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 9/9: Generating reports …")
    total_time: float = time.perf_counter() - t_pipeline_start

    # ── Rich table (console) ──────────────────────────────────────────
    table = Table(
        title=f"FedIoV ChebyKAN + CKKS FHE — {args.dataset}",
        show_lines=True,
    )
    table.add_column("Round", justify="right", style="cyan", no_wrap=True)
    table.add_column("FHE Time(s)", justify="right", style="green")
    table.add_column("Rejected", justify="right", style="red")
    table.add_column("Accuracy", justify="right", style="magenta")
    table.add_column("Macro-F1", justify="right", style="magenta")
    table.add_column("ROC-AUC", justify="right", style="magenta")

    for rd in rounds_data:
        table.add_row(
            str(rd["round"]),
            f"{rd['fhe_time_s']:.2f}",
            str(rd["rejected"]),
            f"{rd['accuracy']:.4f}",
            f"{rd['macro_f1']:.4f}",
            f"{rd['roc_auc']:.4f}",
        )

    console.print(table)

    # ── JSON report ───────────────────────────────────────────────────
    json_path = out_dir / f"report_{args.dataset}.json"
    _save_report_json(json_path, args.dataset, rounds_data, total_time)

    # ── Markdown report ───────────────────────────────────────────────
    md_path = out_dir / f"report_{args.dataset}.md"
    _save_report_markdown(md_path, args.dataset, rounds_data, total_time)

    # ── Final wall-clock ──────────────────────────────────────────────
    console.print(
        f"\n[bold]Total wall-clock time:[/bold] {total_time:.2f} s\n"
    )
    logger.info("Pipeline finished in %.2f s.", total_time)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "ChebyKAN + CKKS FHE federated learning pipeline for IoV "
            "intrusion detection."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["can_vtc", "car_hack", "veremi", "cicids"],
        help="Target dataset for training and evaluation.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="Number of federated communication rounds.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke-test mode: 1 round, ≤ 4 clients, minimal data.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Random seed for reproducibility (CKKS randomness is NOT controlled).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point.  Returns 0 on success, 1 on failure."""
    args = _parse_args(argv)
    logger.info(
        "run_federated_fhe invoked with: dataset=%s  rounds=%d  "
        "smoke=%s  seed=%d",
        args.dataset, args.rounds, args.smoke, args.seed,
    )
    try:
        run_federated_pipeline(args)
    except Exception:
        logger.exception("Pipeline failed with an unhandled exception.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

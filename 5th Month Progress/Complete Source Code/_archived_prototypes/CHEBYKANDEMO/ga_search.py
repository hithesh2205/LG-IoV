"""
ga_search.py — Genetic Algorithm hyperparameter search for ChebyKAN.

This module performs a **plaintext** (no encryption) evolutionary search over
a combinatorial hyperparameter space to find the best ChebyKAN training
configuration.  It runs as a SEPARATE pre-training phase per dataset and
operates on a held-out validation split — NOT inside the encrypted federated
loop.

Search space (~75 600 combinations)
====================================
    batch_size  ∈ {32, 64, 96, 128, 256}                           —  5 choices
    epochs      ∈ {1, 2, 3, 5, 7, 10, 15, 20}                     —  8 choices
    momentum    ∈ {0.80, 0.85, 0.88, 0.90, 0.93, 0.95, 0.99}      —  7 choices
    l2_reg      ∈ {1e-5, 3e-5, 5e-5, 1e-4, 3e-4, 5e-4, 1e-3}     —  7 choices
    dropout     ∈ {0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40,
                   0.45, 0.50}                                     —  9 choices
    optimizer   ∈ {'adam', 'adamw', 'sgd', 'rmsprop'}              —  4 choices

    Total: 5 × 8 × 7 × 7 × 9 × 4 = 70 560  (close to the ~75 000 target)

GA parameters (defaults)
========================
    Population  : 50 (10 in smoke mode)
    Generations : 20 (2 in smoke mode)
    Elitism     : top-5 carried unchanged
    Crossover   : uniform (per-gene coin-flip)
    Mutation    : per-gene random-reset with configurable probability

Output
------
- A rich table showing each generation's best / mean / worst fitness.
- A JSON file ``{dataset_name}_ga_best.json`` with the winning config.
- Returns the best config dict.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from rich.console import Console
from rich.table import Table
from sklearn.metrics import f1_score

from model import ChebyKAN

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search space (~75 600 combinations)
# ---------------------------------------------------------------------------

SEARCH_SPACE: Dict[str, List[Any]] = {
    "batch_size": [32, 64, 96, 128, 256],
    "epochs": [1, 2, 3, 5, 7, 10, 15, 20],
    "momentum": [0.80, 0.85, 0.88, 0.90, 0.93, 0.95, 0.99],
    "l2_reg": [1e-5, 3e-5, 5e-5, 1e-4, 3e-4, 5e-4, 1e-3],
    "dropout": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50],
    "optimizer": ["adam", "adamw", "sgd", "rmsprop"],
}

GENE_NAMES: List[str] = list(SEARCH_SPACE.keys())

# Verify the total combinatorial space.
_TOTAL_COMBOS: int = 1
for _vals in SEARCH_SPACE.values():
    _TOTAL_COMBOS *= len(_vals)
assert _TOTAL_COMBOS == 70_560, (
    f"Expected 70 560 combos in the search space, got {_TOTAL_COMBOS}"
)


# ═══════════════════════════════════════════════════════════════════════════
# Individual dataclass
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class Individual:
    """A single chromosome in the GA population.

    Attributes
    ----------
    genes : dict[str, Any]
        Mapping from hyperparameter name to its current allele value.
    fitness : float
        Validation macro-F1 achieved by this individual.  Defaults to 0.0
        (unevaluated).
    """

    genes: Dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Individual construction helpers
# ═══════════════════════════════════════════════════════════════════════════


def random_individual(rng: np.random.Generator) -> Individual:
    """Sample one random configuration from the search space.

    Parameters
    ----------
    rng : numpy.random.Generator
        Seeded random generator for reproducibility.

    Returns
    -------
    Individual
        A new individual with randomly chosen genes and fitness = 0.0.
    """
    genes: Dict[str, Any] = {
        gene: rng.choice(alleles).item()
        if isinstance(rng.choice(alleles), np.generic)
        else rng.choice(alleles)
        for gene, alleles in SEARCH_SPACE.items()
    }
    logger.debug("random_individual → %s", genes)
    return Individual(genes=genes, fitness=0.0)


def crossover(
    parent_a: Individual,
    parent_b: Individual,
    rng: np.random.Generator,
) -> Individual:
    """Uniform crossover: for each gene, randomly pick from parent_a or parent_b.

    Parameters
    ----------
    parent_a, parent_b : Individual
        The two parents.
    rng : numpy.random.Generator
        Seeded RNG.

    Returns
    -------
    Individual
        A single offspring.
    """
    child_genes: Dict[str, Any] = {}
    for gene in GENE_NAMES:
        if rng.random() < 0.5:
            child_genes[gene] = parent_a.genes[gene]
        else:
            child_genes[gene] = parent_b.genes[gene]
    return Individual(genes=child_genes, fitness=0.0)


def mutate(
    individual: Individual,
    rng: np.random.Generator,
    mutation_prob: float = 0.2,
) -> Individual:
    """For each gene, with probability ``mutation_prob``, replace with a random value.

    The individual is mutated **in-place** and also returned for convenience.

    Parameters
    ----------
    individual : Individual
        The candidate to mutate.
    rng : numpy.random.Generator
        Seeded RNG.
    mutation_prob : float
        Per-gene probability of being replaced.

    Returns
    -------
    Individual
        The (possibly mutated) individual (same object).
    """
    for gene in GENE_NAMES:
        if rng.random() < mutation_prob:
            alleles = SEARCH_SPACE[gene]
            new_val = rng.choice(alleles)
            # Convert numpy scalars to native Python types for JSON safety.
            individual.genes[gene] = (
                new_val.item() if isinstance(new_val, np.generic) else new_val
            )
    return individual


# ═══════════════════════════════════════════════════════════════════════════
# Optimizer factory
# ═══════════════════════════════════════════════════════════════════════════


def _build_optimizer(
    model: nn.Module,
    name: str,
    lr: float,
    momentum: float,
    l2_reg: float,
) -> optim.Optimizer:
    """Construct the optimizer specified by ``name``.

    Parameters
    ----------
    model : nn.Module
        Model whose parameters will be optimised.
    name : str
        One of ``'adam'``, ``'adamw'``, ``'sgd'``, ``'rmsprop'``.
    lr : float
        Learning rate.
    momentum : float
        Momentum (used by SGD and RMSProp; Adam variants ignore it).
    l2_reg : float
        L2 regularisation weight (``weight_decay``).

    Returns
    -------
    torch.optim.Optimizer

    Raises
    ------
    ValueError
        If ``name`` is not recognised.
    """
    name_lower: str = name.lower().strip()
    if name_lower == "adam":
        return optim.Adam(model.parameters(), lr=lr, weight_decay=l2_reg)
    if name_lower == "adamw":
        return optim.AdamW(model.parameters(), lr=lr, weight_decay=l2_reg)
    if name_lower == "sgd":
        return optim.SGD(
            model.parameters(), lr=lr, momentum=momentum, weight_decay=l2_reg
        )
    if name_lower == "rmsprop":
        return optim.RMSprop(
            model.parameters(), lr=lr, momentum=momentum, weight_decay=l2_reg
        )
    raise ValueError(
        f"Unknown optimizer '{name}'. Choose from: adam, adamw, sgd, rmsprop."
    )


# ═══════════════════════════════════════════════════════════════════════════
# Fitness evaluation
# ═══════════════════════════════════════════════════════════════════════════

_MIN_VAL_SAMPLES_FOR_F1: int = 10


def evaluate_fitness(
    individual: Individual,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    n_classes: int,
    device: str = "cpu",
) -> float:
    """Train a ChebyKAN model with the individual's hyperparameters.

    A *fresh* model is created each time — no state leakage between
    evaluations.  Deterministic seeding is applied per evaluation so that
    the same individual always yields the same fitness.

    Parameters
    ----------
    individual : Individual
        The candidate whose genes define the training configuration.
    X_train : numpy.ndarray
        Training features, shape ``(n_train, 46)``.
    y_train : numpy.ndarray
        Training labels, shape ``(n_train,)``.
    X_val : numpy.ndarray
        Validation features, shape ``(n_val, 46)``.
    y_val : numpy.ndarray
        Validation labels, shape ``(n_val,)``.
    n_classes : int
        Number of output classes.
    device : str
        ``'cpu'`` or ``'cuda'``.

    Returns
    -------
    float
        Validation macro-F1 in [0, 1].  Returns 0.0 on training failure.
        Falls back to accuracy if the validation set is too small for
        reliable macro-F1 computation.
    """
    logger.debug("evaluate_fitness — genes=%s", individual.genes)

    # ---- Assertions on input shapes ----------------------------------------
    assert X_train.ndim == 2 and X_train.shape[1] == 46, (
        f"X_train must be (n, 46), got {X_train.shape}"
    )
    assert X_val.ndim == 2 and X_val.shape[1] == 46, (
        f"X_val must be (n, 46), got {X_val.shape}"
    )
    assert y_train.ndim == 1, f"y_train must be 1-D, got {y_train.ndim}-D"
    assert y_val.ndim == 1, f"y_val must be 1-D, got {y_val.ndim}-D"

    config: Dict[str, Any] = individual.genes

    # ---- Deterministic seeding per individual hash -------------------------
    seed_val: int = abs(hash(frozenset(config.items()))) % (2**31)
    torch.manual_seed(seed_val)
    np.random.seed(seed_val % (2**31))

    batch_size: int = int(config["batch_size"])
    epochs: int = int(config["epochs"])
    dropout: float = float(config["dropout"])

    # ---- Build a fresh model -----------------------------------------------
    try:
        model: ChebyKAN = ChebyKAN(
            in_features=46, n_classes=n_classes, dropout=dropout
        )
        model = model.to(device)
    except Exception:
        logger.exception("Model construction failed for config %s", config)
        return 0.0

    criterion: nn.CrossEntropyLoss = nn.CrossEntropyLoss()
    optimizer: optim.Optimizer = _build_optimizer(
        model,
        name=str(config["optimizer"]),
        lr=1e-3,  # fixed LR; GA searches over other knobs
        momentum=float(config["momentum"]),
        l2_reg=float(config["l2_reg"]),
    )

    # ---- Convert numpy → tensors and move to device ------------------------
    X_tr: torch.Tensor = torch.as_tensor(X_train, dtype=torch.float32).to(device)
    y_tr: torch.Tensor = torch.as_tensor(y_train, dtype=torch.long).to(device)
    X_v: torch.Tensor = torch.as_tensor(X_val, dtype=torch.float32).to(device)
    y_v: torch.Tensor = torch.as_tensor(y_val, dtype=torch.long).to(device)

    n_train: int = X_tr.shape[0]

    # ---- Training loop (fresh each evaluation) -----------------------------
    model.train()
    try:
        for _epoch in range(epochs):
            perm: torch.Tensor = torch.randperm(n_train, device=device)
            for start in range(0, n_train, batch_size):
                end: int = min(start + batch_size, n_train)
                idx: torch.Tensor = perm[start:end]
                logits: torch.Tensor = model(X_tr[idx])
                loss: torch.Tensor = criterion(logits, y_tr[idx])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
    except Exception:
        logger.exception("Training failed for config %s", config)
        return 0.0

    # ---- Validation --------------------------------------------------------
    model.eval()
    with torch.no_grad():
        val_logits: torch.Tensor = model(X_v)
        preds: np.ndarray = val_logits.argmax(dim=1).cpu().numpy()
        targets: np.ndarray = y_v.cpu().numpy()

    # Edge case: if the validation set is very small, macro-F1 can be
    # unreliable (e.g. single-class split).  Fall back to raw accuracy.
    if len(targets) < _MIN_VAL_SAMPLES_FOR_F1:
        logger.warning(
            "Validation set too small (%d < %d). Using accuracy instead of macro-F1.",
            len(targets),
            _MIN_VAL_SAMPLES_FOR_F1,
        )
        fitness: float = float(np.mean(preds == targets))
    else:
        fitness = float(
            f1_score(targets, preds, average="macro", zero_division=0)
        )

    logger.debug("evaluate_fitness → %.4f", fitness)
    return fitness


# ═══════════════════════════════════════════════════════════════════════════
# Tournament selection
# ═══════════════════════════════════════════════════════════════════════════


def _tournament_select(
    population: List[Individual],
    rng: np.random.Generator,
    k: int = 3,
) -> Individual:
    """Select one individual via k-tournament selection.

    Parameters
    ----------
    population : list[Individual]
        Current population (must all have evaluated fitness).
    rng : numpy.random.Generator
        Seeded RNG.
    k : int
        Tournament size.

    Returns
    -------
    Individual
        A **deep copy** of the winning individual.
    """
    assert len(population) >= k, (
        f"Population size ({len(population)}) must be ≥ tournament size ({k})"
    )
    indices: np.ndarray = rng.choice(len(population), size=k, replace=False)
    winner_idx: int = int(max(indices, key=lambda i: population[i].fitness))
    return copy.deepcopy(population[winner_idx])


# ═══════════════════════════════════════════════════════════════════════════
# Main GA function
# ═══════════════════════════════════════════════════════════════════════════


def run_genetic_algorithm(
    dataset_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    n_classes: int,
    population_size: int = 50,
    n_generations: int = 20,
    elitism_k: int = 5,
    mutation_prob: float = 0.2,
    smoke: bool = False,
    seed: int = 42,
    device: str = "cpu",
    output_dir: Optional[Path] = None,
) -> dict:
    """Run Genetic Algorithm hyperparameter search.

    In **smoke mode** the population and generation counts are overridden to
    ``population_size=10, n_generations=2`` for fast CI verification.

    Algorithm
    ---------
    1. Initialise a population of random individuals.
    2. For each generation:
       a. Evaluate fitness of all individuals.
       b. Sort by fitness (descending).
       c. Keep top-k (elitism).
       d. Fill remaining slots via tournament selection → crossover → mutation.
       e. Log best / mean / worst fitness.
    3. Return the best individual's genes.
    4. Save to JSON: ``{output_dir}/{dataset_name}_ga_best.json``.

    Parameters
    ----------
    dataset_name : str
        Name tag used for the output JSON filename.
    X_train : numpy.ndarray
        Training features of shape ``(n_train, 46)``.
    y_train : numpy.ndarray
        Training labels of shape ``(n_train,)``.
    X_val : numpy.ndarray
        Validation features of shape ``(n_val, 46)``.
    y_val : numpy.ndarray
        Validation labels of shape ``(n_val,)``.
    n_classes : int
        Number of target classes.
    population_size : int
        Number of individuals per generation.
    n_generations : int
        Number of GA generations.
    elitism_k : int
        Number of top individuals carried unchanged to the next generation.
    mutation_prob : float
        Per-gene probability of random-reset mutation.
    smoke : bool
        If ``True``, use a tiny population (10) and few generations (2).
    seed : int
        Master seed for reproducibility.
    device : str
        ``'cpu'`` or ``'cuda'``.
    output_dir : Path or None
        Directory in which to save the JSON output.  Defaults to the current
        working directory.

    Returns
    -------
    dict
        The best hyperparameter configuration found.  Also saved as
        ``{dataset_name}_ga_best.json`` in ``output_dir``.
    """
    logger.info(
        "run_genetic_algorithm — ENTRY  dataset=%s, smoke=%s, seed=%d",
        dataset_name,
        smoke,
        seed,
    )

    # ---- Smoke-mode overrides ----------------------------------------------
    if smoke:
        population_size = 10
        n_generations = 2
        logger.info("Smoke mode active → population_size=10, n_generations=2")

    # ---- Assertions --------------------------------------------------------
    assert X_train.ndim == 2 and X_train.shape[1] == 46, (
        f"X_train must have 46 features, got shape {X_train.shape}"
    )
    assert X_val.ndim == 2 and X_val.shape[1] == 46, (
        f"X_val must have 46 features, got shape {X_val.shape}"
    )
    assert y_train.ndim == 1, f"y_train must be 1-D, got {y_train.ndim}-D"
    assert y_val.ndim == 1, f"y_val must be 1-D, got {y_val.ndim}-D"
    assert population_size > elitism_k, (
        f"population_size ({population_size}) must exceed elitism_k ({elitism_k})"
    )

    # ---- Output directory --------------------------------------------------
    if output_dir is None:
        output_dir = Path(".")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Master RNG --------------------------------------------------------
    rng: np.random.Generator = np.random.default_rng(seed)

    console: Console = Console()

    console.print(
        f"\n[bold cyan]── GA Search ──[/bold cyan]  "
        f"space={_TOTAL_COMBOS:,} combos │ pop={population_size} │ "
        f"gens={n_generations} │ device={device}\n"
    )
    logger.info(
        "GA config — pop=%d, gens=%d, elitism=%d, mutation_prob=%.2f, device=%s",
        population_size,
        n_generations,
        elitism_k,
        mutation_prob,
        device,
    )

    # ---- Initialise population ---------------------------------------------
    population: List[Individual] = [
        random_individual(rng) for _ in range(population_size)
    ]

    global_best: Individual = Individual(genes={}, fitness=-1.0)

    # ---- Summary table (updated each generation) ---------------------------
    summary_table: Table = Table(
        title="GA Generation Summary",
        show_lines=True,
    )
    summary_table.add_column("Gen", justify="center", style="bold", min_width=5)
    summary_table.add_column("Best F1", justify="right", style="bold green", min_width=9)
    summary_table.add_column("Mean F1", justify="right", style="yellow", min_width=9)
    summary_table.add_column("Worst F1", justify="right", style="red", min_width=9)
    summary_table.add_column("Best Config", style="dim", min_width=40)
    summary_table.add_column("Time (s)", justify="right", min_width=9)

    # ═══════════════════════════════════════════════════════════════════════
    # Generational loop
    # ═══════════════════════════════════════════════════════════════════════
    for gen in range(1, n_generations + 1):
        gen_start: float = time.perf_counter()

        # ---- (a) Evaluate fitness ------------------------------------------
        for idx, ind in enumerate(population):
            f1_val: float = evaluate_fitness(
                individual=ind,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                n_classes=n_classes,
                device=device,
            )
            ind.fitness = f1_val
            logger.debug(
                "Gen %d | Ind %d/%d | F1=%.4f | %s",
                gen,
                idx + 1,
                population_size,
                f1_val,
                ind.genes,
            )

        # ---- (b) Sort by fitness (descending) ------------------------------
        population.sort(key=lambda ind: ind.fitness, reverse=True)

        gen_best: Individual = population[0]
        gen_worst_f1: float = population[-1].fitness
        gen_mean_f1: float = float(np.mean([ind.fitness for ind in population]))

        # ---- Track global best ---------------------------------------------
        if gen_best.fitness > global_best.fitness:
            global_best = copy.deepcopy(gen_best)
            logger.info(
                "New global best @ gen %d: F1=%.4f, config=%s",
                gen,
                global_best.fitness,
                global_best.genes,
            )

        gen_elapsed: float = time.perf_counter() - gen_start

        # ---- Log generation stats ------------------------------------------
        logger.info(
            "Gen %d/%d — best=%.4f, mean=%.4f, worst=%.4f (%.1fs)",
            gen,
            n_generations,
            gen_best.fitness,
            gen_mean_f1,
            gen_worst_f1,
            gen_elapsed,
        )

        # Pretty config string for the table.
        config_str: str = ", ".join(
            f"{k}={v}" for k, v in gen_best.genes.items()
        )
        summary_table.add_row(
            str(gen),
            f"{gen_best.fitness:.4f}",
            f"{gen_mean_f1:.4f}",
            f"{gen_worst_f1:.4f}",
            config_str,
            f"{gen_elapsed:.1f}",
        )

        # ---- (c) Elitism: keep top-k unchanged ----------------------------
        elites: List[Individual] = [
            copy.deepcopy(population[i]) for i in range(elitism_k)
        ]

        # ---- (d) Fill remaining slots via tournament + crossover + mutation
        next_population: List[Individual] = list(elites)

        while len(next_population) < population_size:
            parent_a: Individual = _tournament_select(population, rng)
            parent_b: Individual = _tournament_select(population, rng)
            child: Individual = crossover(parent_a, parent_b, rng)
            child = mutate(child, rng, mutation_prob)
            next_population.append(child)

        population = next_population

    # ═══════════════════════════════════════════════════════════════════════
    # Report & persist the winner
    # ═══════════════════════════════════════════════════════════════════════
    console.print(summary_table)
    console.print()
    console.print(
        f"[bold green]✓ GA Search Complete[/bold green]  "
        f"Best macro-F1 = [bold]{global_best.fitness:.4f}[/bold]"
    )
    console.print(f"  Best config: {global_best.genes}")

    # ---- Save to JSON ------------------------------------------------------
    output_path: Path = output_dir / f"{dataset_name}_ga_best.json"

    serialisable_config: Dict[str, Any] = {}
    for k, v in global_best.genes.items():
        if isinstance(v, float):
            serialisable_config[k] = float(v)
        elif isinstance(v, (int, np.integer)):
            serialisable_config[k] = int(v)
        else:
            serialisable_config[k] = v

    serialisable_config["best_macro_f1"] = float(global_best.fitness)
    serialisable_config["dataset_name"] = dataset_name
    serialisable_config["search_space_size"] = _TOTAL_COMBOS
    serialisable_config["population_size"] = population_size
    serialisable_config["n_generations"] = n_generations
    serialisable_config["seed"] = seed

    output_path.write_text(
        json.dumps(serialisable_config, indent=2), encoding="utf-8"
    )
    logger.info("Best config saved to %s", output_path.resolve())
    console.print(f"  Saved → [link]{output_path.resolve()}[/link]")

    logger.info("run_genetic_algorithm — EXIT")
    return serialisable_config


# ═══════════════════════════════════════════════════════════════════════════
# Standalone CLI / smoke demo
# ═══════════════════════════════════════════════════════════════════════════


def _demo_smoke() -> None:
    """Run a minimal smoke test with synthetic data."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
    )
    console: Console = Console()
    console.print("[bold]GA Smoke Demo — synthetic data[/bold]")

    n_train: int = 200
    n_val: int = 50
    n_features: int = 46
    n_classes: int = 4

    rng: np.random.Generator = np.random.default_rng(42)

    # Synthetic data in [-1, 1] (Chebyshev-compatible).
    X_train: np.ndarray = rng.uniform(-1.0, 1.0, size=(n_train, n_features)).astype(
        np.float32
    )
    y_train: np.ndarray = rng.integers(0, n_classes, size=(n_train,)).astype(np.int64)
    X_val: np.ndarray = rng.uniform(-1.0, 1.0, size=(n_val, n_features)).astype(
        np.float32
    )
    y_val: np.ndarray = rng.integers(0, n_classes, size=(n_val,)).astype(np.int64)

    # Assert 46 dimensions.
    assert X_train.shape[1] == 46, f"Expected 46 features, got {X_train.shape[1]}"
    assert X_val.shape[1] == 46, f"Expected 46 features, got {X_val.shape[1]}"

    # Assert values in [-1, 1].
    assert np.all(X_train >= -1.0) and np.all(X_train <= 1.0), "X_train out of [-1, 1]"
    assert np.all(X_val >= -1.0) and np.all(X_val <= 1.0), "X_val out of [-1, 1]"

    best: dict = run_genetic_algorithm(
        dataset_name="smoke_demo",
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        n_classes=n_classes,
        smoke=True,
        seed=42,
        device="cpu",
    )
    console.print(f"\n[bold green]Returned best config:[/bold green] {best}")


if __name__ == "__main__":
    _demo_smoke()

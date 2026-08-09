"""Genetic-algorithm hyperparameter search — config + population init.

Search space mirrors the paper's GA table (§4):

    batch size              ∈ {12, 24, 48, 96, 192}
    epochs e                ∈ {3, 7, 15, 30, 60}
    momentum                ∈ {0.2, 0.6, 0.85, 0.95, 0.998}
    L2 regularisation       ∈ {5e-5, 5e-4, 5e-3, 5e-2}
    personalisation λ       ∈ {0.15, 0.35, 0.55, 0.75, 0.95}
    crossover probability P_c ∈ {0.65, 0.75, 0.85}
    mutation probability  P_m ∈ {0.02, 0.06, 0.12}
    optimizer               ∈ {rmsprop, adamw, sgd, nadam, adadelta}
    dropout                 ∈ {0.1, 0.2, 0.25, 0.3, 0.4, 0.45}

Phase 1 only **initialises** the population — fitness evaluation,
selection, crossover, mutation are Phase 2+ when local training rounds
exist to drive ``f(φ)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np


# Paper-faithful search grid -----------------------------------------------

GA_SEARCH_SPACE: Dict[str, Sequence] = {
    "batch_size":     (12, 24, 48, 96, 192),
    "epochs":         (3, 7, 15, 30, 60),
    "momentum":       (0.2, 0.6, 0.85, 0.95, 0.998),
    "l2":             (5e-5, 5e-4, 5e-3, 5e-2),
    "personalization":(0.15, 0.35, 0.55, 0.75, 0.95),
    "optimizer":      ("rmsprop", "adamw", "sgd", "nadam", "adadelta"),
    "dropout":        (0.1, 0.2, 0.25, 0.3, 0.4, 0.45),
}

# GA operator probability grid — *not* per-individual genes.
GA_OPERATOR_GRID: Dict[str, Sequence] = {
    "crossover_prob": (0.65, 0.75, 0.85),
    "mutation_prob":  (0.02, 0.06, 0.12),
}


@dataclass
class GAConfig:
    """Top-level GA configuration."""

    population_size: int                 # paper uses N (== n_clients)
    generations: int = 20                # paper §4: G = 20
    crossover_prob: float = 0.85
    mutation_prob: float  = 0.06
    elitism: int = 2                     # carry top-k parents unchanged
    seed: int = 2025
    search_space: Dict[str, Sequence] = field(
        default_factory=lambda: dict(GA_SEARCH_SPACE)
    )

    def summary(self) -> dict:
        return {
            "population_size": self.population_size,
            "generations": self.generations,
            "crossover_prob": self.crossover_prob,
            "mutation_prob": self.mutation_prob,
            "elitism": self.elitism,
            "seed": self.seed,
            "search_space_size": {
                k: len(v) for k, v in self.search_space.items()
            },
            "total_search_space_combinations": int(
                np.prod([len(v) for v in self.search_space.values()])
            ),
        }


# Population utilities -----------------------------------------------------


def sample_individual(
    rng: np.random.Generator,
    search_space: Dict[str, Sequence] = GA_SEARCH_SPACE,
) -> Dict[str, "int|float|str"]:
    """Draw one hyperparameter vector uniformly from the search grid."""
    individual: Dict[str, object] = {}
    for k, choices in search_space.items():
        individual[k] = choices[int(rng.integers(0, len(choices)))]
    return individual  # type: ignore[return-value]


def init_population(cfg: GAConfig) -> List[Dict[str, "int|float|str"]]:
    """Generate ``cfg.population_size`` random individuals."""
    rng = np.random.default_rng(cfg.seed)
    return [sample_individual(rng, cfg.search_space)
            for _ in range(cfg.population_size)]

"""Central hyperparameter config for KANConvNet across IoV datasets.

Defaults follow Heidari et al., FedIoV (FGCS 2026) Tables 3–4.
Per-dataset best hyperparameter sets (Table 4) are exposed via
``DATASET_HPARAMS`` so the same training loop runs on any dataset.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


REPO_ROOT = Path(__file__).resolve().parent
DATA_ROOT = REPO_ROOT.parent / "Preprocessed_Dataset"
CHECKPOINT_DIR = REPO_ROOT / "checkpoints"


# Class labels per dataset (also reported by each adapter at load time,
# but kept here for sanity checks).
CAN_VTC_CLASSES: Tuple[str, ...] = (
    "Attack_free", "DoS_attack", "Fuzzy_attack", "Impersonation_attack",
)
CAR_HACK_CLASSES: Tuple[str, ...] = (
    "normal_run", "DoS", "Fuzzy", "RPM", "gear",
)
CICIDS_BINARY_CLASSES: Tuple[str, ...] = ("BENIGN", "ATTACK")
VEREMI_BINARY_CLASSES: Tuple[str, ...] = ("BENIGN", "ATTACK")


# Paper Table 4 — best hyperparameter set per dataset.
# Keys mirror the CLI flag values: --dataset {can_vtc, car_hack, cicids, veremi}.
DATASET_HPARAMS = {
    "can_vtc":  dict(epochs=40, momentum=0.9,  dropout=0.2,
                     optimizer="rmsprop", layer_size=128),
    "car_hack": dict(epochs=30, momentum=0.85, dropout=0.25,
                     optimizer="adamw",   layer_size=64),
    "cicids":   dict(epochs=60, momentum=0.8,  dropout=0.3,
                     optimizer="sgd",     layer_size=256),
    "veremi":   dict(epochs=25, momentum=0.95, dropout=0.45,
                     optimizer="nadam",   layer_size=128),
}


@dataclass
class DataConfig:
    window: int = 64
    stride: int = 16
    n_features: int = 46
    clip_low: float = 0.005
    clip_high: float = 0.995
    cicids_multi_class: bool = False    # True → many-way label, False → binary


@dataclass
class ModelConfig:
    in_features: int = 46
    n_classes: int = 4                  # overridden per-dataset at runtime
    layer_size: int = 128
    dropout: float = 0.2
    fourier_modes: int = 8
    conv_channels: Tuple[int, int] = (32, 64)
    kernel_size: int = 5
    # Default OFF — unified adapters emit per-window summary (B, 46).
    use_conv_backbone: bool = False


@dataclass
class TrainConfig:
    batch_size: int = 96
    epochs: int = 40
    lr: float = 5e-4
    momentum: float = 0.9
    weight_decay: float = 5e-4
    optimizer: str = "rmsprop"
    val_split: float = 0.15
    test_split: float = 0.15
    seed: int = 2025
    num_workers: int = 2
    device: str = "cuda"
    log_every: int = 50
    save_best: bool = True


@dataclass
class Config:
    dataset: str = "can_vtc"
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)

    def apply_dataset_defaults(self) -> None:
        """Set model.n_classes + train hparams from the chosen dataset."""
        if self.dataset not in DATASET_HPARAMS:
            raise ValueError(f"unknown dataset: {self.dataset!r}")
        hp = DATASET_HPARAMS[self.dataset]
        self.train.optimizer = hp["optimizer"]
        self.train.momentum  = hp["momentum"]
        self.train.epochs    = hp["epochs"]
        self.model.dropout   = hp["dropout"]
        self.model.layer_size = hp["layer_size"]
        # Class count.
        if self.dataset == "can_vtc":
            self.model.n_classes = len(CAN_VTC_CLASSES)
        elif self.dataset == "car_hack":
            self.model.n_classes = len(CAR_HACK_CLASSES)
        elif self.dataset == "cicids":
            self.model.n_classes = len(CICIDS_BINARY_CLASSES) \
                if not self.data.cicids_multi_class else 0  # filled at load
        elif self.dataset == "veremi":
            self.model.n_classes = len(VEREMI_BINARY_CLASSES) \
                if not self.data.cicids_multi_class else 0  # filled at load
        # Keep input-feature width consistent.
        self.model.in_features = self.data.n_features

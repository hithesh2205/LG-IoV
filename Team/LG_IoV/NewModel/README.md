# Privacy-Preserving Adaptive Layer-wise FHE Federated IDS for IoV (MamKANformer Centralized Baseline)

This directory contains the centralized baseline implementation of the **MamKANformer** architecture for intrusion detection in vehicular networks (Internet of Vehicles - IoV). It implements the dataset pipeline, sub-layers, block coupling, and metrics evaluation before moving to a homomorphic federated environment.

## Project Structure

```
NewModel/
  ├── data/
  │     ├── loader.py              # CanFeatureDataset, DataLoader constructor
  │     ├── preprocess.py          # Scaling, percentile clipping, stratification, class weighting
  │     ├── can_features.py        # 46 timeless features extractor (referenced)
  │     ├── can_vtc_dataset.py     # CAN-VTC file parser
  │     ├── car_hack_dataset.py    # Car-Hacking file parser
  │     ├── cicids_dataset.py      # CICIDS-2017 flow column selector
  │     └── veremi_dataset.py      # VeReMi kinematic window parser
  ├── models/
  │     ├── mamba_sublayer.py      # Pure PyTorch Mamba SSM (selective scan)
  │     ├── kan_sublayer.py        # Cubic B-spline Kolmogorov-Arnold Network linear layer
  │     ├── attention_sublayer.py  # Multi-Head Self-Attention sub-layer
  │     ├── mamkanformer_block.py  # Unified MamKANformer block (LN + Mamba + Attention + KAN)
  │     └── mamkanformer.py        # Full Model (Modality Projections, Fusion, Trunk, Readout)
  ├── utils/
  │     ├── metrics.py             # Accuracy, Precision, Recall, F1, ROC-AUC, CM
  │     └── helpers.py             # Random seed fixer, logging, checkpointing
  ├── train.py                     # Training entry point (with early stopping)
  ├── evaluate.py                  # Standalone evaluation entry point
  ├── config.yaml                  # Model and training configuration
  └── requirements.txt             # Dependencies
```

## Architecture Design

### 1. Modality Projection & Fusion
Heterogeneous log data is split into semantic feature groupings (modalities) depending on the dataset. Each modality is projected into a shared `hidden_dim` vector, and these vectors are stacked to construct a sequence of shape `(B, Num_Modalities, hidden_dim)`.
- **CAN Datasets:** Split into Payload, DLC, and CAN-ID.
- **VeReMi:** Split into Kinematics (Means, Stds), Speed Mag, Accel Mag, and Metadata.
- **CICIDS:** Split into Packet Lengths, Durations/IATs, Header sizes, and Flags.

### 2. MamKANformer Block
A single sequence-to-sequence block coupling:
1. **Mamba SSM sub-layer** for selective sequential modeling.
2. **Multi-Head Self-Attention sub-layer** for temporal context modeling.
3. **B-spline KAN sub-layer** as a replacement for standard FFN feedforward networks.
All layers use pre-normalization with LayerNorm, skip connections, and dropout.

### 3. Readout & FHE Hooks
Following the block stack, sequence pooling is applied. The pooled features pass through three sequential post-block KAN layers:
- `KAN Layer 1` (hidden_dim $\to$ layer_size)
- `KAN Layer 2` (layer_size $\to$ layer_size) **[FHE-HOOK]** (adaptive encryption layer inserts here)
- `KAN Layer 3` (layer_size $\to$ layer_size)
Finally, a linear classifier maps features to the target IDS classes.

---

## Setup & Running

### Installation
Ensure you have Python and standard virtual environments active, then install dependencies:
```powershell
pip install -r NewModel/requirements.txt
```

### Run Sanity Smoke Test
To verify the code pipeline, train on any dataset with the `--smoke` flag. This runs 1 epoch on a restricted subset:
```powershell
py NewModel/train.py --dataset can_vtc --smoke
```

### Full Centralized Training
Train the model to convergence (governed by configuration hyper-parameters and early stopping):
```powershell
py NewModel/train.py --dataset can_vtc
```

### Standalone Evaluation
Evaluate a trained model checkpoint on the testing split:
```powershell
py NewModel/evaluate.py --dataset can_vtc --checkpoint NewModel/checkpoints/best_model_can_vtc.pt
```

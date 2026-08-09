# KANConvNet — IoV Intrusion Detection Classifier

Implementation of the **KANConvNet** classifier from
*Heidari, Rastegar, Khonsari — "FedIoV: A secure and adaptive federated
framework for real-time intrusion detection in vehicular networks"*
(Future Generation Computer Systems, 2026), §3.4.

This is the **second stage** of the FedIoV pipeline: a lightweight,
interpretable, Kolmogorov–Arnold–based deep classifier that consumes the
unified per-window feature vectors produced by the preprocessing stage and
outputs an attack-class prediction. The federated aggregation
(TOPSIS + Multi-Krum, §3.x of the paper) is *not* covered here — only the
local classifier each client trains.

## Layout

```
Model/
├── config.py                  hyperparameters (defaults = paper Table 4, CAN row)
├── train.py                   training + evaluation loop
├── requirements.txt
├── models/
│   ├── kan_layers.py          FourierKANLinear, KolmogorovActivation
│   ├── kan_conv.py            KANConv1d  (KAN-style 1-D convolution)
│   └── kanconvnet.py          full classifier (eqs 16–19)
└── data/
    └── can_vtc_dataset.py     CAN-log → windowed 46-feature tensors
```

## Architecture (paper eqs 16–19)

```
   x  ∈ R^46                            input feature vector per window
   z0 = Preprocess(x)                   z-score + clipping  (in DataLoader)
   z1 = W1 · F(z0) + b1                 FourierKANLinear   ← eq. 16
   z2 = σ_Kolmogorov(z1)                KolmogorovActivation ← eq. 17
   z3 z4 z5 = Linear+ReLU stack         hidden refinement
   z6 = W5 · σ_Kolmogorov(z5) + b5      ← eq. 18
   ŷ  = softmax(z6) → argmax            ← eq. 19
```

When the input is a windowed sequence `(B, F, W)`, a short two-stage
`KANConv1d` backbone runs before the head. The Kolmogorov–Arnold trick of
**putting learnable activations on the edges** — not the nodes — is
implemented with a Fourier basis per edge (see `kan_layers.py`).

## Quick start (Windows, PowerShell)

```powershell
cd D:\LG_IoV\Model
py -m pip install -r requirements.txt

# 1-epoch smoke test on 50k rows/class — ~2 minutes on CPU
py train.py --smoke

# Full run (paper defaults: 40 epochs, RMSprop, dropout 0.2, layer 128)
py train.py
```

Outputs land in `checkpoints/`:
- `kanconvnet_best.pt` — best-val-loss weights, normalisation stats, class list.
- `training_log.json` — per-epoch metrics.

## Data expectations

`data/can_vtc_dataset.py` consumes the four HCRL-format CAN logs in
`D:\LG_IoV\Preprocessed_Dataset\Can_vtc_pro\` (auto-extracted from
`Can_vtc_pro.zip` if needed):

- `cleaned_Attack_free_dataset.csv`
- `cleaned_DoS_attack_dataset.csv`
- `cleaned_Fuzzy_attack_dataset.csv`
- `cleaned_Impersonation_attack_dataset.csv`

It computes per-window features (`W=64`, stride `16` — paper §5.2):

| slot | features                                                        |
|------|-----------------------------------------------------------------|
| 0–3  | inter-arrival time: mean, std, min, max                         |
| 4–5  | DLC: mean, std                                                  |
| 6–13 | payload bytes b0..b7 — mean (normalised /255)                   |
| 14–21| payload bytes b0..b7 — std                                      |
| 22–45| CAN-ID histogram over 24 hash buckets                           |

Total = **46 features**, matching paper §3.4's `x ∈ R^46`.

To use a different feature set, swap `_window_features` in
`data/can_vtc_dataset.py` — the model auto-resizes if you set
`Config.data.n_features`.

## Hyperparameters (paper Table 4, CAN row)

| param        | value     |
|--------------|-----------|
| optimizer    | RMSprop   |
| epochs       | 40        |
| momentum     | 0.9       |
| dropout      | 0.2       |
| layer size   | 128       |

Override on the command line or by editing `config.py`.

## Next stage

This module is meant to be wrapped by the federated client. Each client
will instantiate `KANConvNet`, train locally for `E=2` epochs/round,
then ship its `state_dict` (or a DP-noised delta) to the server for
TOPSIS + Multi-Krum aggregation.

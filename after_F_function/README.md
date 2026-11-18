# IoV Intrusion Detection System: ChebyKAN + Federated Learning + CKKS Homomorphic Encryption
## Isolated Benchmark Experiment: `after_F_function`

This directory provides an end-to-end, reproducible implementation and experimental validation of a privacy-preserving Intrusion Detection System (IDS) for the Internet of Vehicles (IoV). It features a **Chebyshev Kolmogorov-Arnold Network (ChebyKAN)**, **Federated Learning (FL)**, and **CKKS Homomorphic Encryption** executing the sample-weighted $F$ aggregation function.

---

## 1. System Architecture & The $F$ Aggregation Function

### The Mathematical Formulation of $F$
In each federated round $t$, $K$ vehicular clients train ChebyKAN locally on their local non-IID or IID data partition and produce model weight differences $\Delta w_k = w_k^{(t+1)} - w^{(t)}$.

Under CKKS homomorphic encryption, each client encrypts its update:
$$c_k = \text{Enc}_{pk}(\Delta w_k)$$

Clients upload $(c_k, n_k)$, where $n_k$ is the local sample count transmitted as an authenticated protocol scalar.

The Roadside Unit (RSU) / Aggregator computes the total sample count:
$$N = \sum_{k=1}^K n_k$$

The **$F$ Aggregation Function** is defined as:
$$\boxed{F(\{c_k, n_k\}_{k=1}^K) = \frac{1}{N} \sum_{k=1}^K n_k c_k}$$

### CKKS-Compatible Execution Steps
Because homomorphic division $\frac{[A]}{[B]}$ is practically impossible in CKKS without severe noise explosion, the RSU executes this function using native ciphertext–plaintext multiplication and ciphertext addition:
1. **Plaintext-Scalar Multiplication:** Each encrypted update $c_k$ is multiplied by its public scalar $n_k$:
   $$c_k' = n_k \odot c_k$$
2. **Homomorphic Ciphertext Addition:**
   $$c_{\text{sum}} = \sum_{k=1}^K c_k'$$
3. **Normalization Multiplication:** Provided $N > 0$, the public scalar $\frac{1}{N}$ is encoded and multiplied into the encrypted sum:
   $$c_F = \left(\frac{1}{N}\right) \odot c_{\text{sum}}$$
4. **Safety Check:** If $N = 0$, the aggregation round is skipped safely, preserving the previous global model.

The resulting ciphertext $c_F$ represents the exact sample-count-weighted average update:
$$\text{Dec}_{sk}(c_F) \approx \frac{\sum_{k=1}^K n_k \Delta w_k}{\sum_{k=1}^K n_k}$$

The global model is updated in the encrypted domain or decrypted by authorized key holders:
$$w^{(t+1)} = w^{(t)} + \eta \cdot \text{Dec}_{sk}(c_F)$$

---

## 2. Key Management Architecture

1. **Key Generation:** A Cloud Trust Authority (CTA) generates the CKKS public/secret key pair (`poly_modulus_degree = 8192`, `coeff_mod_bit_sizes = [60, 40, 40, 60]`, `global_scale = 2^40`).
2. **Public Context Separation:** The secret key is stripped from the context. Only the public context (containing public keys, relinearization keys, and Galois rotation keys) is distributed to vehicular clients and the RSU.
3. **Client Privacy Guarantee:** The RSU possesses **only the public context**. It can perform ciphertext addition and scalar multiplication, but **cannot decrypt** any individual client update $c_k$.
4. **Decryption Authorization:** Only the collective authorized decryptor holds the secret key to decrypt the final aggregate $c_F$.

---

## 3. Directory Layout

```text
after_F_function/
├── README.md                  # This documentation
├── config/
│   ├── base.yaml              # Hyperparameters (ChebyKAN, training, crypto)
│   ├── iid.yaml               # IID partitioning config
│   └── non_iid.yaml           # Non-IID Dirichlet (alpha=0.3) partitioning config
├── src/
│   ├── data/
│   │   ├── can_features.py    # Exact 46-feature extractor
│   │   ├── car_hack.py        # Car-Hacking loader (per-message ground truth)
│   │   ├── preprocess.py      # Group-aware 70/15/15 split, clipping, scaling
│   │   ├── partition.py       # IID and Non-IID Dirichlet partitioning
│   │   └── dataset.py         # PyTorch Dataset & DataLoader wrappers
│   ├── models/
│   │   └── cheby_kan.py       # ChebyshevKAN neural network (degree 4)
│   ├── crypto/
│   │   ├── ckks_context.py    # TenSEAL context & KeyManager
│   │   └── ckks_vector.py     # Whole-vector SIMD packing (11 chunks of 4096)
│   ├── federated/
│   │   ├── client.py          # VehicleClient local training & update packaging
│   │   └── rsu_server.py      # RSUServer executing F aggregation
│   ├── experiments/
│   │   └── runner.py          # Paired experiment coordinator
│   └── utils/
│       ├── metrics.py         # Multi-class Accuracy, F1, Precision, Recall
│       └── helpers.py         # Seeding, YAML loading, JSON saving
├── tests/
│   ├── test_data.py           # Data pipeline, 46-dim, group leakage tests
│   ├── test_model.py          # ChebyKAN forward pass and gradient tests
│   ├── test_f_function.py     # Mathematical equivalence of F function
│   └── test_ckks_equivalence.py # L2 numerical equivalence test (epsilon_agg < 1e-5)
├── scripts/
│   ├── run_smoke.py           # Quick 1-round smoke test
│   ├── run_paired_experiments.py # Runs all 4 paired experiments
│   └── plot_results.py        # Generates comparison plots
├── results/
│   ├── metrics/               # JSON and CSV evaluation metrics
│   ├── plots/                 # PNG charts for convergence and overhead
│   └── checkpoints/           # Model checkpoints
└── reports/
    └── final_report.md        # Comprehensive experimental report
```

---

## 4. How to Reproduce Experiments

Ensure your Python environment has `torch`, `tenseal`, `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, and `pyyaml` installed.

### Step 1: Run Automated Correctness Tests
```bash
python tests/test_data.py
python tests/test_model.py
python tests/test_f_function.py
python tests/test_ckks_equivalence.py
```

### Step 2: Run Smoke Test
```bash
python scripts/run_smoke.py
```

### Step 3: Run Full Paired Experiments
```bash
python scripts/run_paired_experiments.py
```

### Step 4: Generate Publication Plots
```bash
python scripts/plot_results.py
```

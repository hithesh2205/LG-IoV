# Privacy-Preserving Federated IDS for IoV using Single-Key CKKS and ChebyshevKAN

## 📄 Paper Overview
This directory contains the complete, self-contained **IEEE Conference Paper** package (in two-column `IEEEtran` format) covering the entire single-key CKKS homomorphic encryption architecture for the Internet of Vehicles (IoV) collaborative Intrusion Detection System (IDS).

### 📁 Directory Contents
* **`iov_ckks_paper.tex`**: The primary LaTeX manuscript. Includes all sections, formal mathematical models, algorithms, tables, TikZ/pgfplots convergence curves, and figure references.
* **`IEEEtran.cls`**: The official IEEE LaTeX class file (CTAN v1.8b). Ensures compilation without external dependencies.
* **`IEEEtran.bst`**: The official IEEE BibTeX bibliography style file.
* **`figures/`**: Directory containing all high-resolution figures referenced in the manuscript:
  - `01_system_architecture.png`: End-to-end single-key CKKS federated IDS architecture.
  - `02_fhefl_round_protocol.png`: Round protocol execution sequence between vehicles and RSU.
  - `03_data_pipeline_and_defects.png`: 46-D feature extraction and group-aware block splitting.
  - `05_ckks_profile_tradeoff.png`: Practical ($N=8192$) vs. Strict ($N=16384$) profile tradeoffs.
  - `06_month5_results.png`: Empirical results across Car-Hacking, VTC-CAN, CICIDS-2017, and VeReMi.

---

## 🚀 How to Compile

### Option 1: Overleaf (Recommended)
1. Zip the `Paper/` folder (or select `iov_ckks_paper.tex`, `IEEEtran.cls`, and the `figures/` folder).
2. Go to [Overleaf](https://www.overleaf.com), click **New Project** $\rightarrow$ **Upload Project**.
3. Set `iov_ckks_paper.tex` as the main document.
4. Click **Recompile**. Overleaf will compile the complete PDF with all figures, equations, and tables.

### Option 2: Local Command Line (MikTeX / TeXLive)
From this directory, run:
```bash
pdflatex iov_ckks_paper.tex
pdflatex iov_ckks_paper.tex
```
*(Running twice resolves all figure/table labels and cross-references).*

---

## 📊 Summary of Sections & Experimental Evidence in the Paper

| Section | Content & Key Highlights |
| :--- | :--- |
| **I. Introduction** | IoV attack landscape (CAN bus injection, RPM/gear spoofing, V2X misbehaviour), raw telemetry privacy dilemma, honest-but-curious RSU threat model, core contributions. |
| **II. Related Work** | Federated IDS, FHE in machine learning, KAN vs. MLP architectures, non-IID data distribution in vehicular fleets. |
| **III. Threat Model** | Formal assets (A1–A5), five adversary classes (ADV-1 to ADV-5), semi-honest server assumption (AS1), $\le 20\%$ Byzantine bound (AS2), privacy guarantees. |
| **IV. System Architecture** | Trusted Dealer (`setup.py`), Vehicle Client loop (`client.py`), RSU Blind Aggregator (`server.py`), Figs.~\ref{fig:arch} and \ref{fig:protocol}. |
| **V. ChebyshevKAN** | Chebyshev recurrence $T_k(x) = 2x T_{k-1}(x) - T_{k-2}(x)$, linear KAN layer formulation, $14\times$ parameter reduction over MamKANformer (44,164 params). |
| **VI. CKKS Security** | $N=8192$, $\mathbf{q}=[60,40,40,60]$, $\Delta=2^{40}$, 128-bit Ring-LWE security, SIMD packing (4,096 slots/ct), Table~\ref{tab:crypto}, Fig.~\ref{fig:profile_tradeoff}. |
| **VII. Datasets & Pipeline** | Unified 46-D feature representation, group-aware block split to prevent train/test window leakage, Dirichlet non-IID partition ($\alpha=0.3$), Fig.~\ref{fig:pipeline}. |
| **VIII. Experimental Setup** | Hardware specs, hyperparameters, random seeds (2025, 2026, 2027), runtime privacy audit counters. |
| **IX. Results** | Plaintext vs. CKKS benchmark across 4 datasets (Table~\ref{tab:main}), per-round convergence plot (Fig.~\ref{fig:convergence}), timing breakdown (Table~\ref{tab:overhead}), design evolution from Gen-1 Multi-Krum/TOPSIS (Table~\ref{tab:evolution}), Fig.~\ref{fig:all_results}. |
| **X. Discussion** | CAN-VTC separability, VeReMi misbehaviour feature limitation, CKKS approximation error vs. stochastic gradient noise, single-key vs. multi-key roadmap. |
| **XI. Conclusion** | Summary of findings, zero-leakage audit confirmation, and future directions. |
| **References** | 26 citations formatted in standard IEEE style. |

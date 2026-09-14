# FHE Comparison — deliverables

Everything produced for the "FL vs. FL+FHE" comparison and the CKKS math explainer
lives in this folder. The federated-learning **pipeline code itself** stays in
`Team/LG_IoV/NewModel` (it has to — it's wired to the datasets and checkpoints
there), but every *result*, *report*, and *new script* from this work is here.

## What's here

- **`dashboard.html`** — live results dashboard (published as an interactive HTML artifact).
  Accuracy comparison, real CKKS overhead, run status. Rebuild after each new
  training run with `scripts/generate_dashboard_data.py` then `scripts/build_dashboard.py`.
- **`dashboard_template.html`** — the dashboard's source template (edit this, not `dashboard.html`).
- **`ckks_math_walkthrough.html`** — the interactive CKKS math explainer (also published as an Artifact):
  single-key toy example → real polynomial-ring CKKS → real TenSEAL benchmark → multi-key/threshold extension.
- **`nn_training_and_encryption_flow.html`** — animated, autoplaying walkthrough (also published as an Artifact) of
  the ChebyKAN architecture, forward pass + backpropagation, and one full federated round from plaintext through
  encryption, ciphertext aggregation, and back to plaintext. Includes an honest callout about where the current
  simulated code (`fhe_adapter.py` / `server.py`) still touches plaintext server-side during Multi-Krum scoring
  and aggregation-injection, which the deck's "server never sees plaintext" language doesn't fully reflect yet.
- **`results/`** — every JSON result:
  - `federated_summary_<dataset>_fhe.json` / `_nofhe.json` — fresh from-scratch training runs, FHE on/off is the only variable.
  - `real_ckks_benchmark.json` — genuine TenSEAL CKKS timing (encrypt/aggregate/decrypt) on the real ChebyKAN parameter counts.
  - `comparison_summary.json` — the two above, joined per dataset.
  - `dashboard_data.json` — what the dashboard actually reads (generated).
  - `legacy_prior_results/` — the *pre-existing* results that were already in the repo before this session (smoke-scale, 3-round runs) — kept for reference, not part of the fresh comparison.
- **`reports/ChebyKAN_updated_v2_FHE_comparison.pptx`** — a copy of the progress deck with 5 new slides appended (comparison, real CKKS cost, multi-key). The original `ChebyKAN_updated.pptx` is untouched.
- **`scripts/`** — everything used to generate the above:
  - `benchmark_real_ckks.py` — the real TenSEAL benchmark (run from `Team/LG_IoV/NewModel`, needs its dependencies).
  - `build_comparison.py` — joins the fresh training summaries + benchmark into `comparison_summary.json`.
  - `generate_dashboard_data.py` — builds `results/dashboard_data.json`.
  - `build_dashboard.py` — inlines that data into `dashboard_template.html` → `dashboard.html`.
  - `build_pptx_slides.py` — appends the new slides to a copy of the deck.

## What changed in the pipeline itself (`Team/LG_IoV/NewModel`)

- `federated/fhe_adapter.py` — added `PlaintextVector`, a drop-in stand-in for
  `SimulatedCKKSVector` with the same add/mul/decrypt interface but no encryption
  wrapper at all, so FHE on/off can be toggled without touching the aggregation code.
- `federated/server.py`, `federated/client.py` — thread a `use_fhe` flag through
  so the exact same FedAvg + Multi-Krum code path runs either way.
- `train_federated.py` — added `--no-fhe`; output files are now tagged
  `_fhe` / `_nofhe` so both runs can coexist.

## Re-running everything

From `Team/LG_IoV/NewModel`:

```
python train_federated.py --dataset <can_vtc|car_hack|cicids|veremi>          # FHE
python train_federated.py --dataset <...> --no-fhe                            # no-FHE baseline
python benchmark_real_ckks.py
python build_comparison.py
```

Then from this folder's `scripts/`:

```
python generate_dashboard_data.py
python build_dashboard.py
python build_pptx_slides.py     # only after copying the target pptx into place — see the script's DECK_PATH
```

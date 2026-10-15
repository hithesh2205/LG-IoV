# Project video: Privacy-Preserving Collaborative IDS for IoV

A ~5:50 narrated explainer of the whole LGSI IoV project, rendered from code.

**Watch:** `output/LGSI_IoV_Project_Overview.mp4` (1920×1080, 30 fps, narrated, captions burned in)
**Captions file:** `output/LGSI_IoV_Project_Overview.srt` (for YouTube / Teams upload)
**Script with timestamps:** `narration_script.md`

## What the video covers

| # | Section | Content |
|---|---|---|
| — | Title | Project name, the four pillars |
| 1 | The real-world problem | CAN bus has no authentication, the 2015 Jeep Cherokee hack, why fleet data is needed, why federated-learning updates still leak (gradient inversion) |
| 2 | How we do it | Vehicles train ChebyKAN locally → CKKS-encrypt updates → RSU/server aggregates blind (no secret key) with robust weighting → only the aggregate is decrypted |
| 3 | Datasets and preprocessing | Car-Hacking, CAN-VTC, VeReMi, CICIDS-2017 (8.6 GB); per-message labels; 64-message window, stride 16; the 46 features; block-disjoint 70/15/15 split; clipping + z-score; Dirichlet α = 0.3 over 10 vehicles |
| 4 | Attacks | DoS, Fuzzy, RPM and gear spoofing (with measured injection rates); VeReMi's 19 V2X misbehaviours; attacks on the learning itself and their mitigation status |
| 5a | Math: ChebyKAN | MLP edge vs KAN edge, Chebyshev recurrence and T₀…T₄, φ(x) = w_b·x + Σ c_k T_k(tanh x), topology 46→64→64→4, the 44,164-parameter breakdown |
| 5b | Math: CKKS and F | Ring R_q, N = 8192 → 4096 slots, Δ = 2⁴⁰, 11 ciphertexts, the function F step by step, depth 0, proof by linearity, FheFL distance and trust weight, measured costs, noise refresh |
| 6 | Results | 99.77 % vs 99.81 % (Car-Hacking), 95.55 % vs 95.42 % (CICIDS), 8.2 × 10⁻⁷ error, 0 individual decryptions, 3.5 MB / 21× bandwidth, honest limits |
| 7 | Where we stand | Timeline; done items; next: multi-key CKKS (CMK vs DMK compared, TenSEAL → OpenFHE); then hardware (NXP S32G, Raspberry Pi 5, NEON NTT, INT8, on-vehicle IDS); V2X bandwidth, low-magnitude poisoning, DP |
| 8 | Summary | Three-line recap |

Every number comes from the project's own files: `README.md`,
`5th Month Progress/Documentation/` (11 current status, 12 next steps, 08 threat
model, 17 multi-key decision), `5th Month Progress/Dataset/README.md`,
`after_F_function/reports/final_report.md`, and the Oct 8 deck
`Presentation/01_Final_Presentations/08.10.26 Weekly_Meet Final draft.pptx`.

One known discrepancy is shown on screen rather than hidden: the design deck
gives a 4-class model with **44,164** parameters, while the Car-Hacking experiment
uses 5 classes, which gives **44,549**.

## Rebuilding

Requirements: Windows (for the offline SAPI voice), Python 3.12 with numpy,
Pillow, matplotlib and imageio-ffmpeg. The local `.venv` reuses the system
packages.

```bash
.venv/Scripts/python.exe build.py            # full render (~5–10 min) -> output/
.venv/Scripts/python.exe build.py --stills   # quick PNG stills of every scene -> build/stills/
.venv/Scripts/python.exe build.py --scene math_kan   # render one scene only
```

To change what is said, edit `src/narration.py` and rebuild. Only the sentences
you changed are re-synthesised. Each sentence is a caption, or a
`(caption, spoken)` pair when the voice needs a phonetic spelling (for example
"C K K S"). The visuals in `src/scenes.py` appear on sentence cues, so if you
add or remove a sentence, check that scene's builder.

To change the voice or speed, edit `VOICE` / `RATE` in `src/tts.py`. Installed
voices are David, Zira (US) and Hazel (UK). The voice is offline Windows TTS,
so no text leaves the machine.

## Layout

```
video_presentation/
├── build.py              # orchestrates TTS → timeline → render → mux → captions
├── narration_script.md   # generated: the script with timestamps
├── src/
│   ├── narration.py      # the script (single source of truth)
│   ├── scenes.py         # one visual builder per scene
│   ├── engine.py         # drawing helpers, timed elements, ffmpeg renderer
│   └── tts.py            # offline Windows SAPI text-to-speech, cached
├── output/               # final MP4 + SRT
└── build/                # intermediate audio, stills, silent video (safe to delete)
```

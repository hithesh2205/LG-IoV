# Project video: Privacy-Preserving Collaborative IDS for IoV

A ~5:35 animated explainer of the whole LGSI IoV project, rendered from code.
It is told as a story: we follow one vehicle, **Car 7**, through the system.
Along the way it asks the viewer questions ("Is that private enough? Think about
it…"), plays "spot the attack" on a live CAN-bus monitor, and lets the maths
move: curves bend, sliders change coefficients, and result bars race.

**Watch:** `output/LGSI_IoV_Project_Overview.mp4` (1920×1080, 30 fps, female voice, music, burned-in captions)
**Captions file:** `output/LGSI_IoV_Project_Overview.srt` (for YouTube / Teams upload)
**Script with timestamps:** `narration_script.md`

## What the video covers

| # | Scene | Content |
|---|---|---|
| — | Opening | "Your car has dozens of tiny computers — any one could be lying" |
| 1 | Meet Car 7 | Live CAN bus with packets; no passwords, no locks; an attacker drops in, the dashboard needle goes haywire; 2015 Jeep hack with a 1.4 M recall counter; one car alone can't learn enough |
| 2 | Learning together, secretly | Raw data flying to a server gets stamped PRIVATE; federated learning sends only updates; a quick-question pause; gradient inversion; updates get locked (CKKS); locked boxes merge at a keyless server; only the sum is unlocked and a smarter model rides back |
| 3 | Feeding the model | 4 datasets (8.6 GB counter); a live message stream tagged R/T; the 64-message window sliding by 16; 46 feature bars growing (byte stats, DLC, CAN-ID frequencies, entropy); blocks flying into train/val/test bins; data dealt to 10 cars with Dirichlet α = 0.3 mixes |
| 4 | Spot the attack | Scrolling CAN monitor that switches between normal, DoS (ID 0x000), fuzzing and RPM/gear spoofing, with IDS verdicts; VeReMi "ghost car" for the 19 V2X misbehaviours |
| 5a | Curves instead of weights | A weight wobbling on one link morphs into a bendable curve; T₀…T₄ drawn one by one from the recurrence; φ(x) = w_b·x + Σ c_k T_k(tanh x) with live sliders; network with travelling pulses; 44,164 counter |
| 5b | Locked boxes that still add up | Ciphertext as a train with 4,096 seats; scaling by 2⁴⁰ with a worked example; 11 trains; function F step by step with locked boxes; depth 0; same average with and without encryption; distance-based trust weights demoting a poisoned car |
| 6 | Did encryption hurt? | Drum-roll question; "Nope."; racing bars 99.77 % vs 99.81 % (Car-Hacking) and 95.55 % vs 95.42 % (CICIDS); < 1 in a million error; 0 updates decrypted; the update file inflating to 3.5 MB |
| 7 | Where we are, and what's next | Timeline with a sliding "we are here"; done checklist; one shared key splitting into per-car pieces that must all arrive to unlock; TenSEAL → OpenFHE; hardware (NXP S32G, Raspberry Pi 5, NEON NTT, on-vehicle IDS) |
| 8 | Wrap-up | Car 7 and the fleet, three takeaways, Car 7 drives off |

Every number comes from the project's own files: `README.md`,
`5th Month Progress/Documentation/` (11 current status, 12 next steps, 08 threat
model, 17 multi-key decision), `5th Month Progress/Dataset/README.md`,
`after_F_function/reports/final_report.md`, and the Oct 8 deck
`Presentation/01_Final_Presentations/08.10.26 Weekly_Meet Final draft.pptx`.
Illustrative values (sample counts 1,200 / 800 / 2,000, the example weight
0.0183, the CAN frame IDs on screen) are labelled as examples in the video.

## Rebuilding

Requirements: Windows (for the offline SAPI voice), Python 3.12 with numpy,
Pillow, matplotlib and imageio-ffmpeg. The local `.venv` reuses the system
packages.

```bash
.venv/Scripts/python.exe build.py              # full render (~5 min) -> output/
.venv/Scripts/python.exe build.py --no-music   # same, without background music
.venv/Scripts/python.exe build.py --audio-only # re-mix the sound only (~25 s), reusing the last rendered frames
.venv/Scripts/python.exe build.py --stills     # quick PNG stills of every scene -> build/stills/
.venv/Scripts/python.exe build.py --scene idea # render one scene only (silent)
```

- **Changing what is said:** edit `src/narration.py` and rebuild. Only the
  sentences you changed are re-synthesised. A sentence is a caption, or a
  `(caption, spoken)` pair when the voice needs a phonetic spelling, plus an
  optional pause in seconds. Animations are timed to sentences, so if you add or
  remove one, check that scene's builder in `src/scenes.py`.
- **Voice:** `VOICE` / `RATE` in `src/tts.py`. The default is Microsoft Zira
  (female, US). Hazel (female, UK) is also installed. It is offline Windows TTS,
  so no text leaves the machine.
- **Music and sound effects:** generated with numpy in `src/audio.py` (no audio
  files or downloads). The music ducks under the voice.

## Layout

```
video_presentation/
├── build.py              # TTS → timeline → render → soundtrack → mux → captions
├── narration_script.md   # generated: the script with timestamps
├── src/
│   ├── narration.py      # the script (single source of truth)
│   ├── scenes.py         # one animated builder per scene
│   ├── engine.py         # drawing, timed elements, motion helpers, ffmpeg renderer
│   ├── audio.py          # synthesised music + sound effects + final mix
│   └── tts.py            # offline Windows SAPI text-to-speech, cached
├── output/               # final MP4 + SRT
└── build/                # intermediate audio, stills, silent video (safe to delete)
```

"""Offline text-to-speech using the Windows SAPI voices (System.Speech).

Nothing leaves the machine. One WAV is produced per sentence so the captions and
visual cues can be timed exactly to the narration. Results are cached by a hash
of (voice, rate, text), so re-running the build only re-synthesises sentences
whose wording changed.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import wave
from pathlib import Path

VOICE = "Microsoft Zira Desktop"    # female (US). Alternatives: "Microsoft Hazel Desktop" (female, UK), "Microsoft David Desktop"
RATE = 1                            # SAPI rate, -10 (slow) .. 10 (fast); 1 lands the video at ~5:50

_PS = r"""
param([string]$jobs)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$items = Get-Content -Raw -Encoding UTF8 $jobs | ConvertFrom-Json
foreach ($it in $items) {
  $s.SelectVoice($it.voice)
  $s.Rate = [int]$it.rate
  $s.SetOutputToWaveFile($it.out)
  $s.Speak($it.text)
  $s.SetOutputToNull()
}
"""


def _key(text: str) -> str:
    return hashlib.sha1(f"{VOICE}|{RATE}|{text}".encode("utf-8")).hexdigest()[:16]


def synthesize(texts: list[str], out_dir: Path) -> list[Path]:
    """Return one WAV path per text, synthesising only the missing ones."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{_key(t)}.wav" for t in texts]
    todo = [dict(text=t, out=str(p), voice=VOICE, rate=RATE)
            for t, p in zip(texts, paths) if not p.exists()]
    if todo:
        with tempfile.TemporaryDirectory() as td:
            jobs = Path(td) / "jobs.json"
            script = Path(td) / "tts.ps1"
            jobs.write_text(json.dumps(todo), encoding="utf-8")
            script.write_text(_PS, encoding="utf-8")
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", str(script), "-jobs", str(jobs)], check=True)
    return paths


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()

"""Build the LGSI IoV project video.

    .venv/Scripts/python.exe build.py            # full render -> output/
    .venv/Scripts/python.exe build.py --stills   # PNG stills of every scene -> build/stills/
    .venv/Scripts/python.exe build.py --scene math_kan   # render one scene only (quick look)

Pipeline: narration.py -> per-sentence TTS (tts.py) -> timeline -> scene
builders (scenes.py) -> frames piped to ffmpeg -> audio mix + mux -> SRT
captions and a timestamped script.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import imageio_ffmpeg  # noqa: E402

import narration as N  # noqa: E402
import scenes  # noqa: E402
import tts  # noqa: E402
from engine import (C, FPS, H, W, Canvas, El, Renderer, SceneBuild, alpha, blit, font,  # noqa: E402
                    rgba, text_img)

BUILD, OUT = ROOT / "build", ROOT / "output"
VIDEO_NAME = "LGSI_IoV_Project_Overview"
LEAD, GAP, TAIL = 0.8, 0.35, 1.0
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------------ timeline
def make_timeline():
    texts = [N.spoken(s) for sc in N.SCENES for s in sc["sentences"]]
    paths = tts.synthesize(texts, BUILD / "audio")
    t, k, out = 0.0, 0, []
    for sc in N.SCENES:
        lead = 1.0 if sc["id"] == "title" else LEAD
        local, cue, cue_end, sents = lead, [], [], []
        for s in sc["sentences"]:
            d = tts.wav_duration(paths[k])
            cue.append(local)
            cue_end.append(local + d)
            sents.append(dict(wav=paths[k], start=t + local, dur=d, caption=N.caption(s)))
            local += d + GAP
            k += 1
        dur = local - GAP + TAIL
        out.append(dict(sc=sc, start=t, dur=dur, cue=cue, cue_end=cue_end, sents=sents))
        t += dur
    return out, t


# ------------------------------------------------------------------ backgrounds
def base_background():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    c0, c1 = np.array(C["bg0"], float), np.array(C["bg1"], float)
    g = c0 + (c1 - c0) * (0.35 + 0.65 * y)[..., None] * np.ones((1, W, 1))
    glow = np.exp(-(((x - 0.85) ** 2) / 0.08 + ((y - 0.05) ** 2) / 0.10))[..., None]
    g = g + glow * np.array([10, 30, 34])
    img = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    dots = Canvas(W, H, ss=1)
    for yy in range(30, H, 48):
        for xx in range(30, W, 48):
            dots.circle(xx, yy, 1.2, fill=(255, 255, 255, 14))
    img.alpha_composite(dots.img())
    return img


def header(bg, chapter):
    img = bg.copy()
    if chapter is None:
        return img
    blit(img, text_img("LG Soft India  ·  Privacy-Preserving IoV IDS", 20, "semibold", "dim"), 80, 26)
    x = W - 80
    for i in reversed(range(len(N.CHAPTERS))):
        lab = N.CHAPTERS[i]
        cur, past = i == chapter, i < chapter
        t = text_img(lab, 18, "semibold", "bg0" if cur else ("muted" if past else "dim"))
        w, h = t.width + 26, 34
        cv = Canvas(w, h)
        cv.rrect(0, 0, w - 1, h - 1, r=17, fill="teal" if cur else alpha("panel2", 200),
                 outline="teal" if cur else ("border" if past else None), width=2)
        cv.paste(t, 13, 4)
        x -= w
        blit(img, cv.img(), x, 22)
        x -= 8
    return img


def scene_title_els(title, dur):
    if not title:
        return []
    t = text_img(title, 44, "semibold", "text")
    bar = Canvas(90, 6)
    bar.rrect(0, 0, 89, 5, r=3, fill="teal")
    return [El(t, 80, 68, 0.15, dur - 0.45, "left"), El(bar.img(), 82, 68 + t.height + 6, 0.35, dur - 0.45, "wipe")]


def caption_img(text):
    t = text_img(text, 32, "regular", "text", maxw=1500, align="center", spacing=1.25)
    w, h = t.width + 56, t.height + 22
    cv = Canvas(w, h, ss=2)
    cv.rrect(0, 0, w - 1, h - 1, r=14, fill=(5, 9, 18, 200))
    cv.paste(t, 28, 9)
    return cv.img()


# ------------------------------------------------------------------ audio / captions
def mix_audio(tl, total, path):
    rate = 22050
    buf = np.zeros(int((total + 1) * rate), dtype=np.int32)
    for sc in tl:
        for s in sc["sents"]:
            with wave.open(str(s["wav"])) as w:
                assert w.getframerate() == rate and w.getsampwidth() == 2 and w.getnchannels() == 1
                pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
            i = int(s["start"] * rate)
            buf[i:i + len(pcm)] += pcm
    buf = buf[: int(total * rate)]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.clip(buf, -32768, 32767).astype(np.int16).tobytes())


def ts(t, sep=","):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}"


def write_srt(tl, path):
    lines, n = [], 1
    for sc in tl:
        for s in sc["sents"]:
            lines += [str(n), f"{ts(s['start'])} --> {ts(s['start'] + s['dur'])}", s["caption"], ""]
            n += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def write_script(tl, total, path):
    out = [f"# Video narration script ({int(total // 60)}:{int(total % 60):02d})", "",
           "Generated by `build.py` from `src/narration.py`. Timestamps are where each sentence starts.", ""]
    for sc in tl:
        title = sc["sc"]["title"] or "Title"
        out += [f"## {title}  ·  {ts(sc['start'], '.')[3:8]} – {ts(sc['start'] + sc['dur'], '.')[3:8]}", ""]
        for s in sc["sents"]:
            out.append(f"- `{ts(s['start'], '.')[3:8]}` {s['caption']}")
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


# ------------------------------------------------------------------ render
def prepare(tl):
    bg = base_background()
    prepared = []
    for sc in tl:
        S = SceneBuild(cue=sc["cue"], cue_end=sc["cue_end"], dur=sc["dur"])
        scenes.BUILDERS[sc["sc"]["id"]](S)
        els = scene_title_els(sc["sc"]["title"], sc["dur"]) + S.els
        els.sort(key=lambda e: e.z)
        caps = [] if sc["sc"]["id"] == "title" else [
            (s["start"] - sc["start"], (sc["cue"][i + 1] if i + 1 < len(sc["cue"]) else sc["dur"] - 0.5),
             caption_img(s["caption"])) for i, s in enumerate(sc["sents"])]
        prepared.append(dict(sc=sc, bg=header(bg, sc["sc"]["chapter"]), els=els, caps=caps))
    return prepared


def compose(p, t_local, t_global, total, states):
    frame = p["bg"].copy()
    for el, st in zip(p["els"], states):
        if st is not None:
            el.draw(frame, st)
    for a, b, im in p["caps"]:
        if a <= t_local < b:
            blit(frame, im, (W - im.width) / 2, 1048 - im.height)
    pw = int(W * min(1.0, t_global / total))
    bar = Image.new("RGBA", (W, 5), rgba("panel2"))
    bar.paste(Image.new("RGBA", (max(pw, 1), 5), rgba("teal")), (0, 0))
    blit(frame, bar, 0, H - 5)
    return frame


def frame_key(i, p, t_local, t_global, total):
    states = tuple(el.state(t_local) for el in p["els"])
    cap = next((k for k, (a, b, _) in enumerate(p["caps"]) if a <= t_local < b), -1)
    return (i, states, cap, int(W * min(1.0, t_global / total)) // 4), states


def render(tl, total, out_path, only=None):
    prepared = prepare(tl)
    r = Renderer(out_path, FFMPEG)
    t0 = time.time()
    for i, p in enumerate(prepared):
        sc = p["sc"]
        if only and sc["sc"]["id"] != only:
            continue
        f0, f1 = round(sc["start"] * FPS), round((sc["start"] + sc["dur"]) * FPS)
        for f in range(f0, f1):
            tg = f / FPS
            tl_ = tg - sc["start"]
            key, states = frame_key(i, p, tl_, tg, total)
            r.push(key, lambda: compose(p, tl_, tg, total, states))
        print(f"  rendered {sc['sc']['id']:<10} {f1 - f0:>5} frames  ({time.time() - t0:5.0f}s)", flush=True)
    r.close()


def stills(tl, total):
    prepared = prepare(tl)
    d = BUILD / "stills"
    d.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(prepared):
        sc = p["sc"]
        cue = sc["cue"]
        times = sorted(set([cue[j] + 1.2 for j in range(len(cue))] + [sc["dur"] - 0.6]))
        for j, tl_ in enumerate(times):
            tl_ = min(tl_, sc["dur"] - 0.5)
            _, states = frame_key(i, p, tl_, sc["start"] + tl_, total)
            img = compose(p, tl_, sc["start"] + tl_, total, states).convert("RGB")
            img.save(d / f"{i:02d}_{sc['sc']['id']}_{j:02d}.png")
    print(f"stills -> {d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--scene")
    a = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    tl, total = make_timeline()
    print(f"timeline: {len(tl)} scenes, {total:.1f}s ({int(total // 60)}:{int(total % 60):02d})")
    if a.stills:
        stills(tl, total)
        return
    silent = BUILD / ("scene_" + a.scene + ".mp4" if a.scene else "video_silent.mp4")
    render(tl, total, silent, only=a.scene)
    if a.scene:
        print(f"scene preview -> {silent}")
        return
    wav = BUILD / "narration.wav"
    mix_audio(tl, total, wav)
    final = OUT / f"{VIDEO_NAME}.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
                    str(final)], check=True)
    write_srt(tl, OUT / f"{VIDEO_NAME}.srt")
    write_script(tl, total, ROOT / "narration_script.md")
    print(f"done -> {final}")


if __name__ == "__main__":
    main()

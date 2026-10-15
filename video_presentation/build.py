"""Build the LGSI IoV project video.

    .venv/Scripts/python.exe build.py              # full render -> output/
    .venv/Scripts/python.exe build.py --no-music   # same, without background music
    .venv/Scripts/python.exe build.py --audio-only # re-mix sound only, reusing the last rendered frames
    .venv/Scripts/python.exe build.py --stills     # PNG stills of every scene -> build/stills/
    .venv/Scripts/python.exe build.py --scene idea # render one scene only (silent, quick look)

Pipeline: narration.py -> per-sentence TTS (tts.py) -> timeline -> scene
builders (scenes.py) -> frames piped to ffmpeg -> soundtrack (audio.py:
voice + music + effects) -> mux -> SRT captions and a timestamped script.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import imageio_ffmpeg  # noqa: E402

import audio  # noqa: E402
import narration as N  # noqa: E402
import scenes  # noqa: E402
import tts  # noqa: E402
from engine import (C, FPS, H, W, Canvas, Dyn, El, Renderer, SceneBuild, alpha, blit,  # noqa: E402
                    ease_io, rgba, text_img)

BUILD, OUT = ROOT / "build", ROOT / "output"
VIDEO_NAME = "LGSI_IoV_Project_Overview"
LEAD, GAP, TAIL = 0.8, 0.35, 1.0
SWIPE = 0.7          # scene transition length (s), centred on the cut
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
            local += d + GAP + N.pause_after(s)
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
    glow2 = np.exp(-(((x - 0.1) ** 2) / 0.06 + ((y - 0.95) ** 2) / 0.08))[..., None]
    g = g + glow * np.array([10, 30, 34]) + glow2 * np.array([18, 10, 34])
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
    x = W - 80
    for i in reversed(range(len(N.CHAPTERS))):
        cur, past = i == chapter, i < chapter
        t = text_img(N.CHAPTERS[i], 18, "semibold", "bg0" if cur else ("muted" if past else "dim"))
        w, h = t.width + 26, 34
        cv = Canvas(w, h)
        cv.rrect(0, 0, w - 1, h - 1, r=17, fill="teal" if cur else alpha("panel2", 200),
                 outline="teal" if cur else ("border" if past else None), width=2)
        cv.paste(t, 13, 4)
        x -= w
        blit(img, cv.img(), x, 26)
        x -= 8
    return img


def scene_title_els(sc, dur):
    title = sc["title"]
    if not title:
        return []
    num = text_img(f"{sc['chapter'] + 1:02d}", 22, "bold", "teal")
    t = text_img(title, 50, "bold", "text")
    bar = Canvas(90, 6)
    bar.rrect(0, 0, 89, 5, r=3, fill="teal")
    return [El(num, 82, 34, 0.1, dur - 0.45, "fade"),
            El(t, 80, 62, 0.15, dur - 0.45, "left"),
            El(bar.img(), 82, 62 + t.height + 6, 0.35, dur - 0.45, "wipe")]


def caption_img(text):
    t = text_img(text, 31, "semibold", "text", maxw=1500, align="center", spacing=1.25)
    w, h = t.width + 56, t.height + 22
    cv = Canvas(w, h, ss=2)
    cv.rrect(0, 0, w - 1, h - 1, r=16, fill=(5, 9, 18, 205))
    cv.paste(t, 28, 9)
    return cv.img()


def swipe_imgs():
    """Two diagonal bands that sweep across the screen at each scene cut."""
    out = []
    for col, a in (("teal", 255), ("bg1", 255)):
        cv = Canvas(W + 900, H, ss=1)
        cv.polygon([300, 0, W + 900, 0, W + 600, H, 0, H], fill=alpha(col, a))
        out.append(cv.img())
    return out


# ------------------------------------------------------------------ captions / script
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
        title = sc["sc"]["title"] or "Opening"
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
        els = scene_title_els(sc["sc"], sc["dur"]) + S.els
        els.sort(key=lambda e: e.z)
        static = [e for e in els if isinstance(e, El) and not e.top]
        dyn = [e for e in els if isinstance(e, Dyn)]
        top = [e for e in els if isinstance(e, El) and e.top]
        caps = [] if sc["sc"]["id"] == "title" else [
            (s["start"] - sc["start"], (sc["cue"][i + 1] if i + 1 < len(sc["cue"]) else sc["dur"] - 0.5),
             caption_img(s["caption"])) for i, s in enumerate(sc["sents"])]
        prepared.append(dict(sc=sc, bg=header(bg, sc["sc"]["chapter"]), static=static, dyn=dyn, top=top,
                             caps=caps, cache_key=None, cache_img=None))
    return prepared


def sfx_events(tl, prepared):
    ev = []
    for sc, p in zip(tl, prepared):
        if sc["start"] > 0:
            ev.append((sc["start"] - SWIPE / 2, "whoosh"))
        for e in p["static"] + p["top"] + p["dyn"]:
            if e.sfx:
                ev.append((sc["start"] + e.t_in, e.sfx))
    return ev


class Frames:
    def __init__(self, tl, total):
        self.tl, self.total = tl, total
        self.cuts = [sc["start"] for sc in tl[1:]]
        self.swipes = swipe_imgs()

    def swipe_state(self, tg):
        for c in self.cuts:
            if abs(tg - c) < SWIPE / 2 + 0.05:
                return c, int(round((tg - c) * FPS))
        return None

    def state(self, p, t_local, tg):
        st_static = tuple(el.state(t_local) for el in p["static"])
        st_dyn = tuple(el.state(t_local) for el in p["dyn"])
        st_top = tuple(el.state(t_local) for el in p["top"])
        cap = next((k for k, (a, b, _) in enumerate(p["caps"]) if a <= t_local < b), -1)
        prog = int(W * min(1.0, tg / self.total)) // 4
        return (st_static, st_dyn, st_top, cap, prog, self.swipe_state(tg))

    def compose(self, p, t_local, tg, key):
        st_static, st_dyn, st_top, cap, _, sw = key
        if p["cache_key"] != st_static:
            base = p["bg"].copy()
            for el, st in zip(p["static"], st_static):
                if st is not None:
                    el.draw(base, st)
            p["cache_key"], p["cache_img"] = st_static, base
        frame = p["cache_img"].copy()
        for el, st in zip(p["dyn"], st_dyn):
            if st is not None:
                el.draw(frame, st)
        for el, st in zip(p["top"], st_top):
            if st is not None:
                el.draw(frame, st)
        if cap >= 0:
            im = p["caps"][cap][2]
            blit(frame, im, (W - im.width) / 2, 1048 - im.height)
        pw = int(W * min(1.0, tg / self.total))
        bar = Image.new("RGBA", (W, 5), rgba("panel2"))
        bar.paste(Image.new("RGBA", (max(pw, 1), 5), rgba("teal")), (0, 0))
        blit(frame, bar, 0, H - 5)
        if sw is not None:
            c, _ = sw
            for i, im in enumerate(self.swipes):
                q = ease_io((tg - c + SWIPE / 2 - 0.10 * i) / SWIPE)
                blit(frame, im, -im.width + q * (W + im.width), 0)
        return frame


def render(tl, total, out_path, prepared, only=None):
    fr = Frames(tl, total)
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
            key = fr.state(p, tl_, tg)
            r.push((i, key), lambda: fr.compose(p, tl_, tg, key))
        print(f"  rendered {sc['sc']['id']:<10} {f1 - f0:>5} frames  ({time.time() - t0:5.0f}s)", flush=True)
    r.close()


def stills(tl, total, prepared, only=None, step=None):
    fr = Frames(tl, total)
    d = BUILD / "stills"
    d.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(prepared):
        sc = p["sc"]
        if only and sc["sc"]["id"] != only:
            continue
        cue = sc["cue"]
        if step:
            times = list(np.arange(0.5, sc["dur"] - 0.5, step))
        else:
            times = sorted(set([cue[j] + 1.6 for j in range(len(cue))] + [sc["dur"] - 0.6]))
        for j, tl_ in enumerate(times):
            tl_ = min(tl_, sc["dur"] - 0.5)
            tg = sc["start"] + tl_
            key = fr.state(p, tl_, tg)
            fr.compose(p, tl_, tg, key).convert("RGB").save(d / f"{i:02d}_{sc['sc']['id']}_{j:02d}.png")
    print(f"stills -> {d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--step", type=float, help="with --stills: one still every STEP seconds")
    ap.add_argument("--scene")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--audio-only", action="store_true", help="re-mix the soundtrack onto the last silent render")
    a = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    tl, total = make_timeline()
    print(f"timeline: {len(tl)} scenes, {total:.1f}s ({int(total // 60)}:{int(total % 60):02d})")
    prepared = prepare(tl)
    if a.stills:
        stills(tl, total, prepared, a.scene, a.step)
        return
    silent = BUILD / ("scene_" + a.scene + ".mp4" if a.scene else "video_silent.mp4")
    if not (a.audio_only and silent.exists()):
        render(tl, total, silent, prepared, only=a.scene)
    if a.scene:
        print(f"scene preview -> {silent}")
        return
    wav = BUILD / "soundtrack.wav"
    voice = [(s["start"], s["wav"]) for sc in tl for s in sc["sents"]]
    audio.mix(total, voice, sfx_events(tl, prepared), wav, with_music=not a.no_music)
    final = OUT / f"{VIDEO_NAME}.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
                    str(final)], check=True)
    write_srt(tl, OUT / f"{VIDEO_NAME}.srt")
    write_script(tl, total, ROOT / "narration_script.md")
    print(f"done -> {final}")


if __name__ == "__main__":
    main()

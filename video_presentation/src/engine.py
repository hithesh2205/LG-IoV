"""Tiny 2-D motion-graphics engine: drawing helpers, timed elements, renderer.

A scene is a list of elements. Each element is a pre-rendered RGBA image with
an appear time, an optional disappear time and an entrance animation. Frames
are composited with Pillow and piped as raw RGB into ffmpeg. Consecutive frames
whose element states are identical are not recomposited, which keeps the
mostly-static narration frames cheap.
"""
from __future__ import annotations

import io
import math
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

W, H, FPS = 1920, 1080, 30

# ------------------------------------------------------------------ palette
C = dict(
    bg0=(7, 12, 23), bg1=(13, 22, 40),
    panel=(18, 29, 49), panel2=(24, 39, 66), border=(46, 66, 100),
    text=(234, 240, 248), muted=(156, 171, 194), dim=(98, 114, 140),
    teal=(46, 196, 182), blue=(78, 160, 245), amber=(245, 184, 65),
    red=(255, 107, 107), green=(61, 214, 140), violet=(150, 138, 236),
)
# validated categorical series palette (dataviz skill, dark mode, surface #111c2e)
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]


def rgba(c, a=255):
    if c is None:
        return None
    if isinstance(c, str):
        c = C[c]
    return tuple(c) if len(c) == 4 else (*c, a)


def alpha(c, a):
    return (*rgba(c)[:3], a)


# ------------------------------------------------------------------ fonts
FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_FILES = dict(regular="segoeui.ttf", semibold="seguisb.ttf", bold="segoeuib.ttf",
                  light="segoeuil.ttf", italic="segoeuii.ttf", mono="consola.ttf",
                  monob="consolab.ttf", symbol="seguisym.ttf", black="seguibl.ttf")


@lru_cache(maxsize=None)
def font(kind="regular", size=28):
    return ImageFont.truetype(str(FONT_DIR / FONT_FILES[kind]), size)


def wrap(text, fnt, maxw):
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            trial = (cur + " " + w).strip()
            if maxw is None or fnt.getlength(trial) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def text_img(text, size=28, kind="regular", color="text", maxw=None, align="left",
             spacing=1.22, tracking=0):
    """Render (wrapped) text to a tight RGBA image."""
    fnt = font(kind, size)
    lines = wrap(text, fnt, maxw)
    lh = round(size * spacing)
    widths = [fnt.getlength(l) + tracking * max(len(l) - 1, 0) for l in lines]
    w = int(math.ceil(max(widths) if widths else 1)) + 4
    asc, desc = fnt.getmetrics()
    h = lh * (len(lines) - 1) + asc + desc + 4
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (l, lw) in enumerate(zip(lines, widths)):
        x = {"left": 2, "center": (w - lw) / 2, "right": w - lw - 2}[align]
        y = 2 + i * lh
        if tracking:
            for ch in l:
                d.text((x, y), ch, font=fnt, fill=rgba(color))
                x += fnt.getlength(ch) + tracking
        else:
            d.text((x, y), l, font=fnt, fill=rgba(color))
    return im


# ------------------------------------------------------------------ math
plt.rcParams["mathtext.fontset"] = "cm"


@lru_cache(maxsize=None)
def _math_cached(tex, size, color):
    fig = plt.figure(figsize=(0.01, 0.01), dpi=100)
    fig.text(0, 0, f"${tex}$", fontsize=size * 72 / 100, color=np.array(color) / 255)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, transparent=True, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def math_img(tex, size=44, color="text"):
    return _math_cached(tex, size, rgba(color)[:3]).copy()


def fig_to_img(fig, transparent=True):
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, transparent=transparent)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


# ------------------------------------------------------------------ canvas
class Canvas:
    """Supersampled drawing surface; call .img() to get the antialiased result."""

    def __init__(self, w, h, ss=3, bg=(0, 0, 0, 0)):
        self.w, self.h, self.s = int(w), int(h), ss
        self.im = Image.new("RGBA", (self.w * ss, self.h * ss), rgba(bg) if bg else (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.overlays = []

    def _p(self, pts):
        return [v * self.s for v in pts]

    def rrect(self, x0, y0, x1, y1, r=14, fill=None, outline=None, width=2):
        self.d.rounded_rectangle(self._p((x0, y0, x1, y1)), radius=r * self.s, fill=rgba(fill),
                                 outline=rgba(outline), width=int(width * self.s) if outline else 0)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=2):
        self.d.rectangle(self._p((x0, y0, x1, y1)), fill=rgba(fill), outline=rgba(outline),
                         width=int(width * self.s) if outline else 0)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=2):
        self.d.ellipse(self._p((x0, y0, x1, y1)), fill=rgba(fill), outline=rgba(outline),
                       width=int(width * self.s) if outline else 0)

    def circle(self, cx, cy, r, **kw):
        self.ellipse(cx - r, cy - r, cx + r, cy + r, **kw)

    def line(self, pts, color="muted", width=3):
        self.d.line(self._p(pts), fill=rgba(color), width=int(width * self.s), joint="curve")

    def polygon(self, pts, fill=None, outline=None):
        self.d.polygon(self._p(pts), fill=rgba(fill), outline=rgba(outline))

    def arc(self, x0, y0, x1, y1, a0, a1, color="muted", width=3):
        self.d.arc(self._p((x0, y0, x1, y1)), a0, a1, fill=rgba(color), width=int(width * self.s))

    def arrow(self, x0, y0, x1, y1, color="muted", width=4, head=16, dashed=False):
        ang = math.atan2(y1 - y0, x1 - x0)
        bx, by = x1 - head * 0.8 * math.cos(ang), y1 - head * 0.8 * math.sin(ang)
        if dashed:
            L = math.hypot(bx - x0, by - y0)
            n = max(int(L // 18), 1)
            for i in range(n):
                if i % 2 == 0:
                    a, b = i / n, min((i + 1) / n, 1)
                    self.line([x0 + (bx - x0) * a, y0 + (by - y0) * a,
                               x0 + (bx - x0) * b, y0 + (by - y0) * b], color, width)
        else:
            self.line([x0, y0, bx, by], color, width)
        p1 = (x1, y1)
        p2 = (x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45))
        p3 = (x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))
        self.polygon([*p1, *p2, *p3], fill=color)

    def poly_arrow(self, pts, color="muted", width=4, head=16):
        """Polyline whose last segment ends in an arrow head."""
        for i in range(0, len(pts) - 4, 2):
            self.line(pts[i:i + 4], color, width)
        self.arrow(*pts[-4:], color=color, width=width, head=head)

    def text(self, x, y, s, size=26, kind="regular", color="text", anchor="la"):
        self.d.text((x * self.s, y * self.s), s, font=font(kind, size * self.s), fill=rgba(color),
                    anchor=anchor)

    def paste(self, img, x, y, anchor="la"):
        x, y = anchor_xy(img, x, y, anchor)
        self.overlays.append((img, int(x), int(y)))

    def img(self):
        out = self.im.resize((self.w, self.h), Image.LANCZOS)
        for im, x, y in self.overlays:
            blit(out, im, x, y)
        return out


def anchor_xy(img, x, y, anchor):
    w, h = img.size
    ax = {"l": 0, "m": w / 2, "r": w}[anchor[0]]
    ay = {"a": 0, "m": h / 2, "b": h}[anchor[1]]
    return x - ax, y - ay


def blit(dst, src, x, y):
    """alpha_composite that tolerates sources partly outside the destination."""
    x, y = int(round(x)), int(round(y))
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(src.width, dst.width - x), min(src.height, dst.height - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    if (sx0, sy0, sx1, sy1) != (0, 0, src.width, src.height):
        src = src.crop((sx0, sy0, sx1, sy1))
    dst.alpha_composite(src, (x + sx0, y + sy0))


def with_opacity(img, op):
    if op >= 255:
        return img
    a = np.asarray(img.getchannel("A"), dtype=np.uint16) * op // 255
    out = img.copy()
    out.putalpha(Image.fromarray(a.astype(np.uint8)))
    return out


# ------------------------------------------------------------------ components
def card(w, h, title=None, body=None, accent=None, fill="panel", border="border",
         title_size=30, body_size=24, title_color="text", body_color="muted", pad=24, r=18,
         icon=None, body_kind="regular"):
    cv = Canvas(w, h)
    cv.rrect(0, 0, w - 1, h - 1, r=r, fill=fill, outline=border, width=2)
    if accent:
        cv.rrect(0, 0, 8, h - 1, r=4, fill=accent)
    x = pad + (10 if accent else 0)
    y = pad - 4
    if icon is not None:
        cv.paste(icon, x, y + 2)
        x_t = x + icon.width + 14
    else:
        x_t = x
    if title:
        t = text_img(title, title_size, "semibold", title_color, maxw=w - x_t - pad)
        cv.paste(t, x_t, y)
        y += max(t.height, icon.height if icon is not None else 0) + 8
    if body:
        b = text_img(body, body_size, body_kind, body_color, maxw=w - x - pad)
        cv.paste(b, x, y)
    return cv.img()


def pill(text, color="teal", size=24, filled=False, kind="semibold", padx=18, pady=8, text_color=None):
    t = text_img(text, size, kind, text_color or ("bg0" if filled else color))
    w, h = t.width + 2 * padx, t.height + 2 * pady - 4
    cv = Canvas(w, h)
    cv.rrect(0, 0, w - 1, h - 1, r=h // 2, fill=color if filled else alpha(color, 30),
             outline=color, width=2)
    cv.paste(t, padx, pady - 2)
    return cv.img()


def hstack(imgs, gap=16, valign="m"):
    w = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
    h = max(i.height for i in imgs)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for im in imgs:
        y = {"a": 0, "m": (h - im.height) // 2, "b": h - im.height}[valign]
        out.alpha_composite(im, (x, y))
        x += im.width + gap
    return out


def vstack(imgs, gap=12, halign="l"):
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for im in imgs:
        x = {"l": 0, "m": (w - im.width) // 2, "r": w - im.width}[halign]
        out.alpha_composite(im, (x, y))
        y += im.height + gap
    return out


# ------------------------------------------------------------------ icons
def icon_car(w=180, color="blue", body2=None):
    h = int(w * 0.5)
    cv = Canvas(w, h)
    s = w / 180
    cv.polygon([10 * s, 62 * s, 22 * s, 40 * s, 52 * s, 36 * s, 72 * s, 14 * s, 124 * s, 14 * s,
                146 * s, 36 * s, 168 * s, 42 * s, 172 * s, 62 * s, 168 * s, 70 * s, 12 * s, 70 * s],
               fill=color)
    win = body2 or "bg1"
    cv.polygon([62 * s, 36 * s, 78 * s, 20 * s, 96 * s, 20 * s, 96 * s, 36 * s], fill=win)
    cv.polygon([102 * s, 36 * s, 102 * s, 20 * s, 120 * s, 20 * s, 136 * s, 36 * s], fill=win)
    for cx in (46, 136):
        cv.circle(cx * s, 72 * s, 15 * s, fill="bg0")
        cv.circle(cx * s, 72 * s, 11 * s, fill="muted")
        cv.circle(cx * s, 72 * s, 4 * s, fill="bg0")
    cv.rrect(160 * s, 46 * s, 170 * s, 54 * s, r=2 * s, fill="amber")
    return cv.img()


def icon_lock(size=48, color="amber"):
    cv = Canvas(size, size)
    s = size / 48
    cv.arc(13 * s, 3 * s, 35 * s, 27 * s, 180, 360, color=color, width=5 * s)
    cv.line([13 * s, 15 * s, 13 * s, 22 * s], color, 5 * s)
    cv.line([35 * s, 15 * s, 35 * s, 22 * s], color, 5 * s)
    cv.rrect(7 * s, 20 * s, 41 * s, 46 * s, r=5 * s, fill=color)
    cv.circle(24 * s, 31 * s, 4 * s, fill="bg0")
    cv.rect(22.5 * s, 32 * s, 25.5 * s, 39 * s, fill="bg0")
    return cv.img()


def icon_key(size=48, color="amber"):
    cv = Canvas(size, size)
    s = size / 48
    cv.circle(14 * s, 24 * s, 10 * s, outline=color, width=5 * s)
    cv.line([24 * s, 24 * s, 44 * s, 24 * s], color, 5 * s)
    cv.line([38 * s, 24 * s, 38 * s, 33 * s], color, 5 * s)
    cv.line([44 * s, 24 * s, 44 * s, 31 * s], color, 5 * s)
    return cv.img()


def icon_server(w=120, h=150, color="violet"):
    cv = Canvas(w, h)
    rh = (h - 20) / 3
    for i in range(3):
        y = i * (rh + 10)
        cv.rrect(0, y, w - 1, y + rh, r=10, fill="panel2", outline=color, width=3)
        cv.circle(18, y + rh / 2, 5, fill="green")
        cv.line([36, y + rh / 2, w - 18, y + rh / 2], color="border", width=4)
    return cv.img()


def icon_tower(size=110, color="violet"):
    cv = Canvas(size, size)
    s = size / 110
    cv.polygon([55 * s, 30 * s, 35 * s, 104 * s, 75 * s, 104 * s], outline=None, fill=alpha(color, 60))
    cv.line([55 * s, 30 * s, 35 * s, 104 * s], color, 4 * s)
    cv.line([55 * s, 30 * s, 75 * s, 104 * s], color, 4 * s)
    cv.line([42 * s, 78 * s, 68 * s, 78 * s], color, 3 * s)
    cv.circle(55 * s, 28 * s, 7 * s, fill=color)
    for r in (18, 30):
        cv.arc((55 - r) * s, (28 - r) * s, (55 + r) * s, (28 + r) * s, 210, 330, color=color, width=3 * s)
    return cv.img()


def icon_chip(size=90, color="teal"):
    cv = Canvas(size, size)
    s = size / 90
    for i in range(4):
        p = (24 + i * 14) * s
        cv.line([p, 4 * s, p, 18 * s], color, 4 * s)
        cv.line([p, 72 * s, p, 86 * s], color, 4 * s)
        cv.line([4 * s, p, 18 * s, p], color, 4 * s)
        cv.line([72 * s, p, 86 * s, p], color, 4 * s)
    cv.rrect(16 * s, 16 * s, 74 * s, 74 * s, r=8 * s, fill="panel2", outline=color, width=4 * s)
    cv.rrect(32 * s, 32 * s, 58 * s, 58 * s, r=4 * s, fill=color)
    return cv.img()


def icon_shield(size=60, color="green"):
    cv = Canvas(size, size)
    s = size / 60
    cv.polygon([30 * s, 4 * s, 54 * s, 13 * s, 52 * s, 34 * s, 30 * s, 56 * s, 8 * s, 34 * s, 6 * s, 13 * s],
               fill=alpha(color, 70))
    cv.line([30 * s, 4 * s, 54 * s, 13 * s, 52 * s, 34 * s, 30 * s, 56 * s, 8 * s, 34 * s, 6 * s, 13 * s,
             30 * s, 4 * s], color, 4 * s)
    cv.line([19 * s, 30 * s, 27 * s, 38 * s, 42 * s, 22 * s], color, 5 * s)
    return cv.img()


def icon_status(kind, size=34):
    """good / partial / open / bad status glyphs — always paired with a text label."""
    cv = Canvas(size, size)
    s = size / 34
    if kind == "good":
        cv.circle(17 * s, 17 * s, 16 * s, fill="green")
        cv.line([9 * s, 17 * s, 15 * s, 23 * s, 25 * s, 11 * s], "bg0", 4 * s)
    elif kind == "partial":
        cv.circle(17 * s, 17 * s, 15 * s, outline="amber", width=3 * s)
        cv.d.pieslice(cv._p((3 * s, 3 * s, 31 * s, 31 * s)), 90, 270, fill=rgba("amber"))
    elif kind == "bad":
        cv.circle(17 * s, 17 * s, 16 * s, fill="red")
        cv.line([11 * s, 11 * s, 23 * s, 23 * s], "bg0", 4 * s)
        cv.line([23 * s, 11 * s, 11 * s, 23 * s], "bg0", 4 * s)
    elif kind == "warn":
        cv.polygon([17 * s, 2 * s, 33 * s, 31 * s, 1 * s, 31 * s], fill="amber")
        cv.line([17 * s, 12 * s, 17 * s, 21 * s], "bg0", 4 * s)
        cv.circle(17 * s, 26 * s, 2.3 * s, fill="bg0")
    elif kind == "todo":
        cv.circle(17 * s, 17 * s, 15 * s, outline="muted", width=3 * s)
    return cv.img()


# ------------------------------------------------------------------ timeline
def ease(p):
    return 1 - (1 - p) ** 3


@dataclass
class El:
    img: Image.Image
    x: float
    y: float
    t_in: float
    t_out: float | None = None
    anim: str = "up"          # fade | up | down | left | right | wipe | wipe_rl | wipe_tb
    dur: float = 0.5
    out_dur: float = 0.35
    z: int = 0

    def state(self, t):
        if t < self.t_in:
            return None
        p = min(1.0, (t - self.t_in) / self.dur)
        e = ease(p)
        op = e
        if self.t_out is not None and t >= self.t_out:
            q = min(1.0, (t - self.t_out) / self.out_dur)
            if q >= 1:
                return None
            op *= 1 - q
        dx = dy = 0
        wipe = 1.0
        a = self.anim
        if a == "up":
            dy = (1 - e) * 26
        elif a == "down":
            dy = -(1 - e) * 26
        elif a == "left":
            dx = -(1 - e) * 40
        elif a == "right":
            dx = (1 - e) * 40
        elif a.startswith("wipe"):
            wipe = e
            op = (1.0 if p > 0 else 0.0) * (op / e if e > 0 else 0)
        return (int(round(op * 255)), int(round(dx)), int(round(dy)), int(round(wipe * 400)))

    def draw(self, frame, st):
        op, dx, dy, wq = st
        if op <= 0:
            return
        img, x, y = self.img, self.x + dx, self.y + dy
        if wq < 400:
            f = wq / 400
            if self.anim == "wipe":
                img = img.crop((0, 0, max(1, int(img.width * f)), img.height))
            elif self.anim == "wipe_rl":
                cut = int(img.width * (1 - f))
                img = img.crop((cut, 0, img.width, img.height))
                x += cut
            elif self.anim == "wipe_tb":
                img = img.crop((0, 0, img.width, max(1, int(img.height * f))))
        blit(frame, with_opacity(img, op), x, y)


@dataclass
class Dyn:
    """Element redrawn every frame by fn(local_t) -> list[(img, x, y)]."""
    fn: Callable
    t_in: float
    t_out: float | None = None
    fade: float = 0.4
    z: int = 0

    def state(self, t):
        if t < self.t_in or (self.t_out is not None and t >= self.t_out + self.fade):
            return None
        op = min(1.0, (t - self.t_in) / self.fade)
        if self.t_out is not None and t > self.t_out:
            op *= 1 - (t - self.t_out) / self.fade
        return (int(op * 255), round((t - self.t_in) * FPS))

    def draw(self, frame, st):
        op, _ = st
        lt = st[1] / FPS
        for img, x, y in self.fn(lt):
            blit(frame, with_opacity(img, op), x, y)


@dataclass
class SceneBuild:
    """What a scene builder fills in. Times are relative to the scene start."""
    cue: list
    cue_end: list
    dur: float
    els: list = field(default_factory=list)

    def add(self, img, x, y, at, anim="up", out=None, anchor="la", dur=0.5, z=0):
        x, y = anchor_xy(img, x, y, anchor)
        el = El(img, x, y, at, out if out is not None else self.dur - 0.45, anim, dur, z=z)
        self.els.append(el)
        return el

    def dyn(self, fn, at, out=None, z=0):
        self.els.append(Dyn(fn, at, out if out is not None else self.dur - 0.45, z=z))


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self, out_path: Path, ffmpeg: str, crf=18, preset="medium"):
        self.p = subprocess.Popen(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", preset,
             "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)],
            stdin=subprocess.PIPE)
        self._last_key = None
        self._last_bytes = None
        self.frames = 0

    def push(self, key, compose: Callable[[], Image.Image]):
        if key != self._last_key:
            self._last_bytes = compose().convert("RGB").tobytes()
            self._last_key = key
        self.p.stdin.write(self._last_bytes)
        self.frames += 1

    def close(self):
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError("ffmpeg failed")

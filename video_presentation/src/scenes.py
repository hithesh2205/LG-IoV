"""Visual builders, one per narration scene — animated explainer style.

Every builder receives a ``SceneBuild``: ``cue[i]`` / ``cue_end[i]`` are the
start / end (seconds, scene-local) of sentence ``i``. ``at(S, i, f)`` gives a
moment a fraction ``f`` of the way through sentence ``i``, which is how
animations are synced to particular words.

Positions are absolute 1920x1080 frame coordinates. Content area: x 80..1840,
y ~170..920 (header above, captions below).
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from engine import (C, SERIES, W, Canvas, alpha, back_out, card, clamp01, ease, ease_io, hstack,
                    icon_car, icon_chip, icon_key, icon_lock, icon_server, icon_shield, icon_status,
                    lerp, math_img, pill, rgba, text_img, vstack)

X0, X1 = 80, 1840
CW = X1 - X0


def T(s, size=26, kind="regular", color="text", **kw):
    return text_img(s, size, kind, color, **kw)


def M(tex, size=44, color="text"):
    return math_img(tex, size, color)


def at(S, i, f=0.0):
    return S.cue[i] + f * (S.cue_end[i] - S.cue[i])


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def panel(w, h, fill="panel", border="border", r=20, width=2):
    cv = Canvas(w, h)
    cv.rrect(0, 0, w - 1, h - 1, r=r, fill=fill, outline=border, width=width)
    return cv


def over(base, top):
    out = base.copy()
    out.alpha_composite(top)
    return out


# =================================================================== icons
def car7(w=200, color="blue", badge="7"):
    im = icon_car(w, color)
    if not badge:
        return im
    s = w / 180
    b = Canvas(im.width, im.height)
    b.circle(92 * s, 50 * s, 12 * s, fill="amber")
    b.text(92 * s, 50 * s, badge, max(8, int(15 * s)), "bold", "bg0", anchor="mm")
    return over(im, b.img())


def lock_glyph(cv, cx, cy, s, color, opened=False):
    if opened:
        cv.arc(cx - 9 * s, cy - 20 * s, cx + 9 * s, cy - 2 * s, 180, 330, color=color, width=4 * s)
        cv.line([cx - 9 * s, cy - 11 * s, cx - 9 * s, cy - 4 * s], color, 4 * s)
    else:
        cv.arc(cx - 9 * s, cy - 20 * s, cx + 9 * s, cy - 2 * s, 180, 360, color=color, width=4 * s)
        cv.line([cx - 9 * s, cy - 11 * s, cx - 9 * s, cy - 4 * s], color, 4 * s)
        cv.line([cx + 9 * s, cy - 11 * s, cx + 9 * s, cy - 4 * s], color, 4 * s)
    cv.rrect(cx - 14 * s, cy - 6 * s, cx + 14 * s, cy + 16 * s, r=4 * s, fill=color)


def box_locked(size=64, color="amber", label=None, opened=False):
    cv = Canvas(size, size)
    cv.rrect(2, 2, size - 3, size - 3, r=size * 0.2, fill=color)
    if label:
        # big label in the middle, small lock badge in the corner
        lock_glyph(cv, size * 0.8, size * 0.24, size / 150, "bg0", opened)
    else:
        lock_glyph(cv, size / 2, size / 2 + 2, size / 64, "bg0", opened)
    im = cv.img()
    if label:
        t = T(label, max(16, int(size * 0.5)), "black", "bg0")
        im = over(im, _center_on(t, size, size, dy=size * 0.06))
    return im


def _center_on(t, w, h, dy=0):
    out = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    out.alpha_composite(t, (int((w - t.width) / 2), int((h - t.height) / 2 + dy)))
    return out


def doc_icon(size=54, pin=False):
    w, h = size, int(size * 1.25)
    cv = Canvas(w, h)
    cv.polygon([2, 2, w * 0.68, 2, w - 2, w * 0.32, w - 2, h - 2, 2, h - 2], fill=(214, 224, 238))
    cv.polygon([w * 0.68, 2, w * 0.68, w * 0.32, w - 2, w * 0.32], fill=(160, 175, 198))
    for i in range(4):
        y = h * (0.42 + 0.13 * i)
        cv.line([w * 0.16, y, w * (0.84 if i % 2 == 0 else 0.6), y], (120, 136, 160), 3)
    im = cv.img()
    if pin:
        p = Canvas(w, h)
        cx, cy, r = w * 0.7, h * 0.28, w * 0.22
        p.polygon([cx - r * 0.8, cy + r * 0.5, cx + r * 0.8, cy + r * 0.5, cx, cy + r * 2.0], fill="red")
        p.circle(cx, cy, r, fill="red")
        p.circle(cx, cy, r * 0.42, fill=(255, 235, 235))
        im = over(im, p.img())
    return im


def model_glyph(size=60, color="teal"):
    cv = Canvas(size, size)
    cv.rrect(2, 2, size - 3, size - 3, r=size * 0.22, fill=alpha(color, 50), outline=color, width=3)
    L = [(size * 0.28, size * (0.3 + 0.2 * i)) for i in range(3)]
    R = [(size * 0.72, size * (0.38 + 0.24 * i)) for i in range(2)]
    for a in L:
        for b in R:
            cv.line([*a, *b], color, 2)
    for x, y in L + R:
        cv.circle(x, y, size * 0.07, fill=color)
    return cv.img()


def update_packet(size=46):
    cv = Canvas(size, size)
    cv.rrect(2, 2, size - 3, size - 3, r=size * 0.22, fill="teal")
    cv.text(size / 2, size / 2, "Δw", int(size * 0.42), "bold", "bg0", anchor="mm")
    return cv.img()


def hacker(size=90):
    cv = Canvas(size, size)
    s = size / 90
    cv.polygon([45 * s, 4 * s, 82 * s, 40 * s, 76 * s, 86 * s, 14 * s, 86 * s, 8 * s, 40 * s], fill="red")
    cv.ellipse(24 * s, 30 * s, 66 * s, 74 * s, fill="bg0")
    cv.ellipse(31 * s, 46 * s, 41 * s, 54 * s, fill="red")
    cv.ellipse(49 * s, 46 * s, 59 * s, 54 * s, fill="red")
    return cv.img()


def bubble(text, color="red", size=34):
    t = T(text, size, "bold", "bg0")
    w, h = t.width + 30, t.height + 14
    cv = Canvas(w, h + 14)
    cv.rrect(0, 0, w - 1, h - 1, r=h / 2, fill=color)
    cv.polygon([w * 0.3, h - 2, w * 0.45, h - 2, w * 0.3, h + 12], fill=color)
    cv.paste(t, 15, 5)
    return cv.img()


def crossed(img, color="red", strike=False):
    """Diagonal cross-out for icons; strike=True gives a readable strike-through for text pills."""
    cv = Canvas(img.width, img.height)
    if strike:
        cv.line([10, img.height / 2, img.width - 10, img.height / 2], color, 3)
    else:
        m = img.width * 0.12
        cv.line([m, m, img.width - m, img.height - m], color, max(4, img.width * 0.08))
    return over(img, cv.img())


def magnifier(size=80, color="red"):
    cv = Canvas(size, size)
    s = size / 80
    cv.circle(32 * s, 32 * s, 22 * s, fill=alpha(color, 40), outline=color, width=6 * s)
    cv.line([48 * s, 48 * s, 72 * s, 72 * s], color, 9 * s)
    return cv.img()


def frame_cell(label, bad=False, w=58, h=64, tag=None):
    cv = Canvas(w, h + (20 if tag else 0))
    cv.rrect(0, 0, w - 1, h - 1, r=8, fill=alpha("red", 80) if bad else (40, 58, 90),
             outline="red" if bad else None, width=2)
    cv.text(w / 2, h / 2, label, 17, "monob", "red" if bad else (170, 186, 208), anchor="mm")
    if tag:
        cv.text(w / 2, h + 10, tag, 14, "monob", "red" if bad else "muted", anchor="mm")
    return cv.img()


def dim_overlay(a=170):
    return Image.new("RGBA", (W, 1080), (4, 8, 16, a))


# =================================================================== title
def b_title(S):
    c, e = S.cue, S.cue_end
    S.add(T("LG SOFT INDIA  ·  IoV INTRUSION DETECTION PROJECT", 22, "semibold", "teal", tracking=3),
          W / 2, 120, at=0.2, anchor="ma", anim="fade")
    car = car7(440)
    cx, cy = W / 2, 330
    S.move(car, [(-300, cy), (cx, cy)], 0.15, 1.5, ease_fn=ease, sfx="whoosh")
    # tiny computers pop around the car
    ring = [(-330, -60), (-260, 110), (0, -165), (260, 110), (330, -60), (0, 175)]
    chip = icon_chip(54, "teal")
    for i, (dx, dy) in enumerate(ring):
        S.add(chip, cx + dx, cy + dy, at=c[0] + 0.5 + 0.18 * i, anim="pop", anchor="mm", out=c[1],
              sfx="pop" if i == 0 else None)
    lie = at(S, 0, 0.62)
    S.add(icon_chip(54, "red"), cx + ring[3][0], cy + ring[3][1], at=lie, anim="pop", anchor="mm", out=c[1])
    S.add(bubble("lying!", "red", 26), cx + ring[3][0] + 10, cy + ring[3][1] - 40, at=lie + 0.2, anim="pop",
          anchor="lb", out=c[1], sfx="alert")
    S.add(T("Can a fleet of cars catch hackers", 66, "bold"), W / 2, 560, at=c[1] + 0.2, anchor="ma")
    S.add(T("without sharing their secrets?", 66, "bold", "teal"), W / 2, 646, at=c[1] + 0.9, anchor="ma",
          sfx="pop")
    tags = hstack([pill("Federated learning", "blue"), pill("CKKS encryption", "amber"),
                   pill("ChebyKAN", "teal"), pill("Robust aggregation", "violet")], gap=18)
    S.add(tags, W / 2, 770, at=at(S, 1, 0.75), anchor="ma", anim="pop")
    small = car7(110, "blue", None)
    for i in range(5):
        x = 360 + i * 300
        S.move(small, [(W + 200 + i * 160, 930), (x, 930)], c[1] + 0.6 + 0.12 * i, c[1] + 2.0 + 0.12 * i)


# =================================================================== problem
_BUS = 400


def gauge_dial(size=170):
    cv = Canvas(size, size * 0.62)
    cx, cy, r = size / 2, size * 0.56, size * 0.44
    cv.arc(cx - r, cy - r, cx + r, cy + r, 180, 360, color="border", width=10)
    cv.arc(cx - r, cy - r, cx + r, cy + r, 315, 360, color="red", width=10)
    for k in range(9):
        a = math.pi * (1 - k / 8)
        cv.line([cx + (r - 18) * math.cos(a), cy - (r - 18) * math.sin(a),
                 cx + (r - 6) * math.cos(a), cy - (r - 6) * math.sin(a)], "muted", 3)
    return cv.img()


def b_problem(S):
    c, e = S.cue, S.cue_end
    px, py, pw, ph = X0, 180, 1060, 720
    bgp = panel(pw, ph)
    bgp.paste(T("Inside Car 7", 28, "semibold", "muted"), 30, 22)
    sil = icon_car(980, (40, 60, 100))
    a = np.asarray(sil.getchannel("A"), dtype=np.uint16) * 70 // 255
    sil.putalpha(Image.fromarray(a.astype(np.uint8)))
    bgp.paste(sil, 40, 150)
    cv = Canvas(pw, ph)
    cv.line([60, _BUS, 1000, _BUS], (96, 128, 180), 10)
    cv.text(60, _BUS - 42, "CAN bus", 24, "semibold", (130, 160, 210))
    ecus = [("Engine", 220, 230), ("Brakes", 500, 230), ("Steering", 780, 230), ("Infotainment", 760, 520)]
    for name, x, y in ecus:
        stub = (y + 80, _BUS) if y < _BUS else (_BUS, y)
        cv.line([x, stub[0], x, stub[1]], (96, 128, 180), 4)
        cv.rrect(x - 100, y, x + 100, y + 80, r=16, fill="panel2", outline="blue", width=3)
        cv.text(x, y + 40, name, 25, "semibold", "text", anchor="mm")
    cv.line([330, _BUS, 330, 500], (96, 128, 180), 4)
    cv.rrect(220, 500, 440, 650, r=16, fill="panel2", outline="blue", width=3)
    cv.text(330, 626, "Dashboard", 22, "semibold", "text", anchor="mm")
    S.add(over(bgp.img(), cv.img()), px, py, at=0.2, anim="up")
    S.add(car7(150), px + pw - 30, py + 18, at=c[0] + 0.3, anim="pop", anchor="ra", sfx="pop")

    # speedometer on the dashboard
    dial = gauge_dial(170)
    dcx, dcy = px + 330, py + 500 + 18 + 170 * 0.56
    t_attack = at(S, 2, 0.35)
    needles = {}

    def needle(t):
        if t < t_attack:
            v = 0.32 + 0.02 * math.sin(t * 2.1)
        else:
            v = clamp01(0.32 + (t - t_attack) * 1.6) * 0.62 + 0.3 + 0.06 * math.sin(t * 23)
            v = min(v, 0.98)
        key = round(v, 3)
        im = needles.get(key)
        if im is None:
            n = Canvas(170, 110, ss=2)
            a = math.pi * (1 - v)
            r = 170 * 0.44 - 20
            n.line([85, 95, 85 + r * math.cos(a), 95 - r * math.sin(a)], "red" if v > 0.75 else "amber", 5)
            n.circle(85, 95, 8, fill="text")
            im = needles[key] = n.img()
        return [(dial, dcx - 85, py + 512), (im, dcx - 85, py + 512 + 95 * 0 + 0)]

    S.dyn(needle, at=0.4)

    # packets on the bus
    ok, bad = Canvas(40, 20), Canvas(40, 20)
    ok.rrect(0, 0, 39, 19, r=6, fill="teal")
    bad.rrect(0, 0, 39, 19, r=6, fill="red")
    ok, bad = ok.img(), bad.img()
    t_hack = at(S, 2, 0.2)

    def packets(t):
        out = []
        for i in range(9):
            x = (t * 170 + i * 105) % 920 + 70
            out.append((ok, px + x - 20, py + _BUS - 10))
        if t > t_hack:
            for i in range(6):
                x = 900 - ((t - t_hack) * 260 + i * 150) % 840
                out.append((bad, px + x - 20, py + _BUS - 10))
        return out

    S.dyn(packets, at=0.6)

    # attacker drops in
    hk = hacker(96)
    hx, hy = px + 930, py + 560
    S.move(hk, [(hx, py - 120), (hx, hy)], t_hack - 0.5, t_hack, ease_fn=ease, sfx="alert")
    st = Canvas(10, 120)
    st.line([5, 0, 5, 120], "red", 4)
    S.add(st.img(), hx - 5, py + _BUS, at=t_hack, anim="wipe_tb")
    # confused ECUs
    for k, (name, x, y) in enumerate(ecus[:3]):
        S.add(bubble("?!", "red", 24), px + x + 60, py + y - 18, at=at(S, 2, 0.55) + 0.15 * k, anim="pop",
              anchor="lb")

    # right column: swapping cards
    rx, rw = 1180, X1 - 1180
    k0 = panel(rw, 300)
    k0.paste(T("This is Car 7", 34, "bold"), 30, 26)
    k0.paste(T("~70–100 control units", 26, "semibold", "teal"), 30, 90)
    k0.paste(T("all on one shared wire, all listening to every message", 22, "regular", "muted", maxw=rw - 60),
             30, 134)
    S.add(k0.img(), rx, 220, at=c[0] + 0.8, anim="right", out=c[1])

    k1 = panel(rw, 420)
    k1.paste(T("The CAN bus trusts everyone", 32, "bold"), 30, 26)
    S.add(k1.img(), rx, 220, at=c[1], anim="right", out=c[3])
    S.add(crossed(icon_key(110, "amber")), rx + 90, 340, at=at(S, 1, 0.55), anim="pop", sfx="pop")
    S.add(T("No passwords", 26, "semibold"), rx + 145, 470, at=at(S, 1, 0.55), anim="fade", anchor="ma",
          out=c[3])
    S.add(crossed(icon_lock(110, "amber")), rx + 370, 340, at=at(S, 1, 0.8), anim="pop", sfx="pop")
    S.add(T("No locks", 26, "semibold"), rx + 425, 470, at=at(S, 1, 0.8), anim="fade", anchor="ma", out=c[3])
    S.add(T("Anyone can talk. Everyone believes.", 24, "regular", "red"), rx + 30, 560, at=at(S, 2, 0.4),
          anim="fade", out=c[3])

    k3 = panel(rw, 470, border="red")
    k3.paste(pill("BREAKING  ·  2015", "red", 22, filled=True), 30, 26)
    k3.paste(T("Jeep hacked remotely on a highway", 30, "bold", maxw=rw - 60), 30, 92)
    k3.paste(T("cars recalled", 26, "semibold", "muted"), 30, 300)
    S.add(k3.img(), rx, 220, at=c[3], anim="right", out=c[4], sfx="alert")
    S.counter(rx + 30, 410, at(S, 3, 0.55), at(S, 3, 0.9), 0, 1_400_000, size=84, out=c[4], sfx=None)
    S.add(Image.new("RGBA", (1, 1)), 0, 0, at=at(S, 3, 0.9), sfx="ding")

    k4 = panel(rw, 470, border="teal")
    k4.paste(icon_shield(80, "teal"), 30, 26)
    k4.paste(T("Car 7 needs a guard", 32, "bold"), 130, 46)
    k4.paste(T("attacks seen by one car", 22, "regular", "muted"), 30, 150)
    S.add(k4.img(), rx, 220, at=c[4], anim="right")
    track = Canvas(rw - 60, 26)
    track.rrect(0, 0, rw - 61, 25, r=13, fill="panel2")
    S.add(track.img(), rx + 30, 410, at=c[4] + 0.2, anim="fade")
    fill_img = Canvas(rw - 60, 26)
    fill_img.rrect(0, 0, (rw - 61) * 0.16, 25, r=13, fill="red")
    S.add(fill_img.img(), rx + 30, 410, at=at(S, 4, 0.45), anim="wipe", dur=0.8)
    S.add(T("not enough to learn from", 22, "semibold", "red"), rx + 30, 446, at=at(S, 4, 0.55), anim="fade")
    fleet = hstack([icon_car(70, "blue") for _ in range(6)], gap=10)
    S.add(fleet, rx + 30, 520, at=at(S, 4, 0.75), anim="pop", sfx="pop")
    S.add(T("…so let the whole fleet learn together", 22, "semibold", "teal"), rx + 30, 580,
          at=at(S, 4, 0.85), anim="fade")


# =================================================================== idea
def b_idea(S):
    c, e = S.cue, S.cue_end
    car_y = [300, 500, 700]
    cars = [car7(190, "blue", None), car7(190, "blue", "7"), car7(190, "blue", None)]
    sx, sy = 1560, 480
    for i, (y, im) in enumerate(zip(car_y, cars)):
        S.add(im, 210, y, at=0.2 + 0.15 * i, anim="pop", anchor="mm")
    S.add(icon_server(150, 190, "violet"), sx, sy, at=0.4, anim="pop", anchor="mm")
    S.add(T("Server", 24, "semibold", "muted"), sx, sy + 110, at=0.6, anim="fade", anchor="ma")
    paths = [[(330, y), (sx - 100, sy - 60 + 60 * i)] for i, y in enumerate(car_y)]

    # 1) raw data flying to the server
    d_plain, d_pin = doc_icon(50), doc_icon(50, pin=True)
    t_pin = at(S, 1, 0.3)
    for i in range(3):
        def docs(t, P=paths[i], off=i * 0.3):
            items = []
            for k in range(2):
                p = ((t - c[0]) / 2.2 + k / 2 + off) % 1.0
                x, y = P[0][0] + (P[1][0] - P[0][0]) * p, P[0][1] + (P[1][1] - P[0][1]) * p
                im = d_pin if t > t_pin else d_plain
                items.append((im, x - 25, y - 31, min(1, p / 0.1, (1 - p) / 0.1)))
            return items
        S.dyn(docs, at=c[0] + 0.2, out=c[2] - 0.2)
    S.add(T("send all the raw data?", 30, "semibold", "amber"), 880, 260, at=c[0] + 0.4, anim="fade",
          anchor="ma", out=c[1] + 0.8)
    stamp = Canvas(380, 150)
    stamp.rrect(4, 4, 375, 145, r=24, outline="red", width=8, fill=alpha("red", 40))
    stamp.text(190, 75, "PRIVATE!", 58, "black", "red", anchor="mm")
    S.add(stamp.img(), 880, 480, at=at(S, 1, 0.55), anim="pop", anchor="mm", out=c[2] - 0.2, sfx="alert",
          top=True)

    # 2) federated: data stays, updates travel
    for i, y in enumerate(car_y):
        S.add(doc_icon(40, pin=True), 345, y - 50, at=c[2] + 0.3, anim="pop", out=c[5] - 0.1)
        S.add(model_glyph(44), 345, y + 6, at=c[2] + 0.5, anim="pop", out=c[5] - 0.1)
    S.add(T("data stays home", 20, "semibold", "teal"), 300, 795, at=c[2] + 0.6, anim="fade", out=c[5] - 0.1)
    S.add(T("only what the model learned travels", 28, "semibold", "teal"), 880, 260, at=c[2] + 1.0,
          anim="fade", anchor="ma", out=c[3])
    upd, lck = update_packet(46), box_locked(50)
    t_lock = at(S, 4, 0.85)
    for i in range(3):
        def ups(t, P=paths[i], off=i * 0.27):
            items = []
            for k in range(2):
                p = ((t - c[2]) / 2.0 + k / 2 + off) % 1.0
                x, y = P[0][0] + 50 + (P[1][0] - P[0][0] - 50) * p, P[0][1] + (P[1][1] - P[0][1]) * p
                im = lck if t > t_lock else upd
                items.append((im, x - 24, y - 24, min(1, p / 0.1, (1 - p) / 0.1)))
            return items
        S.dyn(ups, at=c[2] + 1.2, out=c[5] - 0.1)

    # 3) quick question
    S.add(dim_overlay(), 0, 0, at=c[3], anim="fade", out=c[4] - 0.1, top=True, dur=0.3)
    q = panel(820, 330, fill="panel2", border="amber", width=3)
    q.paste(pill("QUICK QUESTION", "amber", 22, filled=True), 40, 36)
    q.paste(T("Is that private enough?", 52, "bold"), 40, 120)
    q.paste(T("think about it…", 26, "regular", "muted"), 40, 210)
    S.add(q.img(), W / 2, 500, at=c[3], anim="pop", anchor="mm", out=c[4] - 0.1, top=True, sfx="pop")
    t_q0, t_q1 = e[3], c[4] - 0.1
    rings = {}

    def countdown(t):
        f = clamp01((t - t_q0) / max(t_q1 - t_q0, 0.1))
        k = int(f * 40)
        im = rings.get(k)
        if im is None:
            cv = Canvas(120, 120, ss=2)
            cv.circle(60, 60, 48, outline="border", width=9)
            if k:
                cv.arc(12, 12, 108, 108, -90, -90 + 360 * k / 40, color="amber", width=9)
            im = rings[k] = cv.img()
        return [(im, W / 2 + 260, 500 - 60)]
    S.dyn(countdown, at=c[3] + 0.3, out=c[4] - 0.1)

    # 4) inversion: a spy rebuilds the data from an update
    # (kept above the packet paths, which cross the middle of the screen)
    S.add(magnifier(80, "red"), 700, 250, at=c[4] + 0.2, anim="pop", anchor="mm", out=c[5] - 0.1, sfx="alert")
    S.add(T("→", 40, "bold", "red"), 770, 250, at=at(S, 4, 0.35), anim="fade", anchor="mm", out=c[5] - 0.1)
    S.add(doc_icon(52, pin=True), 830, 250, at=at(S, 4, 0.45), anim="pop", anchor="mm", out=c[5] - 0.1)
    S.add(T("updates can be inverted back into your data", 24, "semibold", "red"), 660, 176, at=c[4] + 0.5,
          anim="fade", out=c[5] - 0.1)
    S.add(Image.new("RGBA", (1, 1)), 0, 0, at=t_lock, sfx="click")
    S.add(pill("so we lock them", "amber", 24, filled=True), 900, 228, at=t_lock, anim="pop",
          out=c[5] - 0.1)

    # 5) locked boxes go to the server and merge without opening
    big = box_locked(84, label="Σ")
    slot_y = [sy - 70, sy, sy + 70]
    mx, my = sx - 190, sy
    t_merge = at(S, 5, 0.55)
    for i, y in enumerate(car_y):
        t0 = c[5] + 0.2 + 0.25 * i
        S.move(box_locked(56), [(330, y), (mx - 40, slot_y[i])], t0, t0 + 1.3, out=t_merge)
        S.move(box_locked(56), [(mx - 40, slot_y[i]), (mx, my)], t_merge, t_merge + 0.5, at=t_merge,
               out=t_merge + 0.5)
    S.add(big, mx, my, at=t_merge + 0.45, anim="pop", anchor="mm", out=c[6] + 0.3, sfx="pop")
    nk = hstack([crossed(icon_key(54, "amber")), T("no key", 26, "bold", "red")], gap=10)
    S.add(nk, sx, sy - 175, at=at(S, 5, 0.85), anim="pop", anchor="mm", sfx="pop")
    S.add(T("adds locked boxes without opening them", 24, "semibold", "amber"), 880, 260, at=c[5] + 0.4,
          anim="fade", anchor="ma", out=c[6])

    # 6) unlock only the sum; smarter model rides back
    S.add(box_locked(84, "teal", label="Σ", opened=True), mx, my, at=c[6] + 0.3, anim="pop", anchor="mm",
          sfx="click")
    mg = model_glyph(56, "green")
    for i, y in enumerate(car_y):
        t0 = at(S, 6, 0.4) + 0.2 * i
        S.move(mg, [(mx, my + 60), (880, 860 if i == 2 else 780), (330, y + 40)], t0, t0 + 1.6)
        S.add(icon_status("good", 40), 120, y - 70, at=t0 + 1.6, anim="pop",
              sfx="ding" if i == 0 else None)
    S.add(T("smarter model for every car  ·  then the next round", 26, "semibold", "green"), 880, 260,
          at=at(S, 6, 0.5), anim="fade", anchor="ma")


# =================================================================== data
def b_data(S):
    c, e = S.cue, S.cue_end
    sets = [("Car-Hacking", "17 M CAN messages", "blue"), ("CAN-VTC", "4.6 M CAN messages", "violet"),
            ("VeReMi", "24 M V2X beacons", "amber"), ("CICIDS-2017", "2.8 M IP flows", "dim")]
    cw = (CW - 3 * 20) // 4
    for i, (name, sub, col) in enumerate(sets):
        cv = panel(cw, 124, border=col)
        cv.paste(doc_icon(44), 22, 22)
        cv.paste(T(name, 28, "bold"), 84, 20)
        cv.paste(T(sub, 22, "regular", "muted"), 84, 64)
        S.add(cv.img(), X0 + i * (cw + 20), 176, at=c[0] + 1.0 + 0.2 * i, anim="down",
              sfx="pop" if i == 0 else None)
    S.counter(X1, 66, at(S, 0, 0.6), at(S, 0, 0.95), 0, 8.6, fmt="{:.1f} GB", size=52, color="teal",
              anchor="ra")
    S.add(pill("main benchmark", "blue", 18, filled=True), X0 + 20, 286, at=c[1] + 0.3, anim="pop")

    # live message stream
    rng = np.random.default_rng(3)
    nmsg = 60
    inj = rng.random(nmsg) < 0.22
    ids = ["316", "18F", "260", "2A0", "329", "545", "43F", "2C0", "370", "4B1", "153", "220"]
    cells = [frame_cell("000" if inj[i] and i % 3 == 0 else rng.choice(ids), bad=bool(inj[i]),
                        tag="T" if inj[i] else "R") for i in range(nmsg)]
    pitch, sy0 = 64, 350
    t_freeze = c[2] + 0.4
    x_lo, x_hi = X0, 1110

    def stream_x(t):
        tt = min(t, t_freeze) - c[1]
        return x_hi - tt * 110

    def stream(t):
        base = stream_x(t)
        out = []
        for i, im in enumerate(cells):
            x = base + i * pitch - 1500
            if x_lo - 60 < x < x_hi:
                o = min(1.0, (x - x_lo + 60) / 80, (x_hi - x) / 60)
                out.append((im, x, sy0, max(0, o)))
        return out
    S.dyn(stream, at=c[1] + 0.2)
    S.add(T("each message tagged:  R = normal,  T = injected", 21, "regular", "muted"), X0, 450,
          at=c[1] + 0.8, anim="fade")

    # sliding window
    # 8 drawn cells stand for the 64-message window; a step of 2 cells stands for 16 messages
    win = Canvas(8 * pitch + 8, 104)
    win.rrect(2, 2, win.w - 3, 101, r=10, outline="amber", width=5)
    win = win.img()
    base_frozen = stream_x(t_freeze)
    first = int(math.ceil((x_lo + 20 - (base_frozen - 1500)) / pitch))

    def window(t):
        k = min(int(max(0, t - t_freeze - 0.2) / 0.7), 3)
        x = base_frozen - 1500 + (first + 2 * k) * pitch - 4
        return [(win, x, sy0 - 10)]
    S.dyn(window, at=t_freeze)
    S.add(T("64 messages  ·  step 16", 22, "semibold", "amber"), X0, 488, at=t_freeze + 0.2, anim="fade")

    # 46-number feature vector
    fx, base_y = 1190, 560
    groups = [(16, SERIES[0], "byte stats (16)"), (2, SERIES[4], "DLC (2)"),
              (26, SERIES[2], "CAN-ID frequencies (26)"), (2, SERIES[3], "entropy (2)")]
    heights = np.abs(np.sin(np.arange(46) * 1.7)) * 110 + 30
    cols = []
    for n, col, _ in groups:
        cols += [hexrgb(col)] * n
    bars = []
    for i in range(46):
        b = Canvas(11, int(heights[i]))
        b.rrect(0, 0, 10, int(heights[i]) - 1, r=3, fill=cols[i])
        bars.append(b.img())
    t_sq = at(S, 2, 0.55)
    arrow = Canvas(70, 40)
    arrow.arrow(0, 20, 64, 20, color="amber", width=5, head=18)
    S.add(arrow.img(), 1115, 362, at=t_sq - 0.2, anim="wipe")

    def feats(t):
        out = []
        for i, im in enumerate(bars):
            p = clamp01((t - t_sq - i * 0.035) / 0.35)
            if p > 0:
                h = max(1, int(im.height * ease(p)))
                out.append((im.crop((0, 0, im.width, h)), fx + i * 14, base_y - h))
        return out
    S.dyn(feats, at=t_sq)
    S.add(T("46 numbers per window", 26, "bold", "amber"), fx, 352, at=t_sq + 0.3, anim="fade")
    legend_pos = [(fx, base_y + 14), (fx + 250, base_y + 14), (fx, base_y + 44), (fx + 330, base_y + 44)]
    for k, ((n, col, lab), (lx_, ly_)) in enumerate(zip(groups, legend_pos)):
        item = hstack([_sq(col), T(lab, 19, "semibold", "text")], gap=8)
        S.add(item, lx_, ly_, at=at(S, 3, 0.1 + 0.22 * k), anim="pop", sfx="pop" if k == 0 else None)

    # block split into bins, then deal to ten cars
    t4 = c[4]
    bins = [("train 70 %", "teal", X0, 430), ("val 15 %", "blue", X0 + 450, 180), ("test 15 %", "amber", X0 + 650, 180)]
    for name, col, bx, bw in bins:
        bb = Canvas(bw, 120)
        bb.line([2, 0, 2, 116, bw - 3, 116, bw - 3, 0], col, 4)
        S.add(bb.img(), bx, 760, at=t4 + 0.1, anim="fade")
        S.add(T(name, 22, "semibold", col), bx + bw / 2, 888, at=t4 + 0.1, anim="fade", anchor="ma")
    order = ["tr"] * 14 + ["va"] * 3 + ["te"] * 3
    rng2 = np.random.default_rng(5)
    rng2.shuffle(order)
    counts = {"tr": 0, "va": 0, "te": 0}
    colmap = {"tr": "teal", "va": "blue", "te": "amber"}
    binx = {"tr": X0 + 14, "va": X0 + 464, "te": X0 + 664}
    S.add(T("blocks of messages", 20, "semibold", "muted"), X0, 652, at=t4, anim="fade", out=t4 + 3.0)
    for i, o in enumerate(order):
        blk = Canvas(36, 36)
        blk.rrect(0, 0, 35, 35, r=7, fill=colmap[o])
        blk = blk.img()
        k = counts[o]
        counts[o] += 1
        per_row = 10 if o == "tr" else 4
        tx = binx[o] + (k % per_row) * 40 + 18
        ty = 850 - (k // per_row) * 40 - 18
        t0 = t4 + 0.6 + i * 0.09
        S.move(blk, [(X0 + 18 + i * 44, 700), (tx, ty)], t0, t0 + 0.7, at=t4 + 0.2)

    # Dirichlet: ten cars, each with a different mix
    mix = rng2.dirichlet([0.3] * 5, size=10)
    names = ["Normal", "DoS", "Fuzzy", "RPM", "Gear"]
    cx0 = 990
    t_deal = at(S, 4, 0.55)
    small = icon_car(64, "blue")
    for v in range(10):
        x = cx0 + v * 76
        S.add(small, x, 868, at=t_deal - 0.3 + 0.05 * v, anim="pop")
        segs = []
        y = 0
        for k in range(5):
            h = mix[v, k] * 150
            segs.append((y, h, hexrgb(SERIES[k])))
            y += h
        col_img = Canvas(52, 142)
        for y, h, col in segs:
            h *= 140 / 150
            y *= 140 / 150
            if h >= 1.5:
                col_img.rect(0, 140 - y - h + 1, 51, 140 - y, fill=col)
        col_img = col_img.img()

        def grow(t, im=col_img, x=x, t0=t_deal + 0.08 * v):
            p = ease(clamp01((t - t0) / 0.6))
            h = max(1, int(im.height * p))
            return [(im.crop((0, im.height - h, im.width, im.height)), x + 6, 856 - h)]
        S.dyn(grow, at=t_deal + 0.08 * v)
    leg = hstack([hstack([_sq(SERIES[k]), T(n, 18, "regular")], gap=6) for k, n in enumerate(names)], gap=16)
    S.add(leg, cx0, 682, at=t_deal + 0.5, anim="fade")
    S.add(T("10 cars · Dirichlet α = 0.3 · every car sees a different mix", 20, "semibold", "muted"),
          cx0, 652, at=t_deal + 0.6, anim="fade")


def _sq(col):
    s = Canvas(16, 16)
    s.rrect(0, 0, 15, 15, r=4, fill=hexrgb(col))
    return s.img()


# =================================================================== attacks
def b_attacks(S):
    c, e = S.cue, S.cue_end
    mx, my, mw, mh = X0, 180, CW, 360
    mon = panel(mw, mh, fill=(12, 20, 36), border="border")
    mon.paste(T("CAN BUS MONITOR", 22, "bold", "muted", tracking=2), 60, 24)
    S.add(mon.img(), mx, my, at=0.2)

    def live(t):
        on = (t * 2) % 2 < 1.2
        d = Canvas(20, 20)
        d.circle(10, 10, 8, fill="red" if on else alpha("red", 70))
        return [(d.img(), mx + 30, my + 28)]
    S.dyn(live, at=0.3)

    modes = [(0, "normal"), (at(S, 1, 0.1), "dos"), (at(S, 2, 0.05), "fuzzy"), (at(S, 3, 0.1), "spoof"),
             (c[4] + 0.2, "normal")]

    def mode_at(t):
        m = "normal"
        for t0, name in modes:
            if t >= t0:
                m = name
        return m

    ids = ["316", "18F", "260", "2A0", "329", "545", "43F", "2C0", "370", "4B1", "153", "220"]
    cache = {}

    def cell(label, bad):
        k = (label, bad)
        if k not in cache:
            cache[k] = frame_cell(label, bad, w=66, h=78)
        return cache[k]

    speed, pitch = 260, 76
    x_left, x_right = mx + 30, mx + mw - 30

    def stream(t):
        out = []
        head = t * speed
        j_hi = int(head // pitch)
        for j in range(j_hi - 26, j_hi + 1):
            x = x_right - (head - j * pitch)
            if x < x_left - 70 or x > x_right:
                continue
            t_enter = j * pitch / speed
            m = mode_at(t_enter)
            r = (j * 2654435761) % 1000 / 1000
            label, bad = ids[j % len(ids)], False
            if m == "dos" and j % 2 == 0:
                label, bad = "000", True
            elif m == "fuzzy" and r < 0.45:
                label, bad = f"{(j * 7919) % 0x7FF:03X}", True
            elif m == "spoof" and j % 3 == 1:
                label, bad = ("RPM" if j % 2 else "GEAR"), True
            o = min(1.0, (x - x_left + 70) / 90, (x_right - x) / 40)
            out.append((cell(label, bad), x, my + 90, max(0, o)))
        return out
    S.dyn(stream, at=0.4)

    verdicts = [(0.6, "IDS:  normal traffic", "green"), (at(S, 1, 0.45), "IDS:  DoS attack detected!", "red"),
                (at(S, 2, 0.4), "IDS:  fuzzing detected!", "red"),
                (at(S, 3, 0.45), "IDS:  spoofing detected!", "red"), (c[4] + 0.4, "IDS:  all four caught", "green")]
    for k, (t0, txt, col) in enumerate(verdicts):
        t1 = verdicts[k + 1][0] if k + 1 < len(verdicts) else None
        ic = icon_status("good" if col == "green" else "warn", 40)
        im = hstack([ic, T(txt, 34, "bold", col)], gap=14)
        S.add(im, mx + 60, my + 220, at=t0, anim="pop", out=t1, sfx=("alert" if col == "red" else None))
    S.add(T("spot the attack!", 26, "semibold", "amber"), mx + mw - 40, my + 24, at=c[0] + 0.4, anim="fade",
          anchor="ra", out=at(S, 1, 0.45))

    # result cards
    cw, ch = (CW - 3 * 20) // 4, 300
    y0 = 570
    specs = [("Denial of service", "floods top-priority ID 0x000", "24 % of frames", at(S, 1, 0.5)),
             ("Fuzzing", "random IDs, random payloads", "13 % of frames", at(S, 2, 0.45)),
             ("RPM / gear spoofing", "fake engine-speed and gear readings", "19 % / 18.5 % of frames",
              at(S, 3, 0.5))]
    for i, (title, body, rate, t0) in enumerate(specs):
        cv = panel(cw, ch, border="red")
        cv.paste(T(title, 27, "bold", maxw=cw - 50), 24, 22)
        cv.paste(T(body, 21, "regular", "muted", maxw=cw - 50), 24, 92)
        cv.paste(T(rate, 22, "semibold", "red", maxw=cw - 50), 24, ch - 60)
        S.add(cv.img(), X0 + i * (cw + 20), y0, at=t0, anim="up")
        S.add(icon_status("good", 44), X0 + i * (cw + 20) + cw - 30, y0 + 16, at=c[4] + 0.5 + 0.2 * i,
              anim="pop", anchor="ra", sfx="pop" if i == 0 else None)
    vx = X0 + 3 * (cw + 20)
    vc = panel(cw, ch, border="violet")
    vc.paste(T("V2X misbehaviour", 27, "bold"), 24, 22)
    vc.paste(T("VeReMi · 19 types, e.g. fake positions, replayed beacons", 20, "regular", "muted",
               maxw=cw - 48), 24, 66)
    t_v = at(S, 4, 0.4)
    S.add(vc.img(), vx, y0, at=t_v, anim="up", sfx="pop")
    ghost_c = icon_car(110, "violet")
    real_c = icon_car(110, "blue")
    spots = [(vx + 40, y0 + 190), (vx + 230, y0 + 150), (vx + 120, y0 + 220), (vx + 250, y0 + 220)]

    def ghost(t):
        k = int((t - t_v) / 0.7) % len(spots)
        f = ((t - t_v) / 0.7) % 1.0
        gx, gy = spots[k]
        return [(real_c, vx + 40, y0 + 190, 1.0), (ghost_c, gx, gy - 40, 0.55 * min(1, f * 4, (1 - f) * 4))]
    S.dyn(ghost, at=t_v + 0.3)
    S.add(T("ghost", 18, "semibold", "violet"), vx + cw - 30, y0 + ch - 34, at=t_v + 0.8, anim="fade",
          anchor="ra")


# =================================================================== math: ChebyKAN
def cheb(k, x):
    if k == 0:
        return np.ones_like(x)
    if k == 1:
        return x
    a, b = np.ones_like(x), x
    for _ in range(k - 1):
        a, b = b, 2 * x * b - a
    return b


def coeffs(t):
    """Slowly wandering coefficients (w_b, c0..c4) used by the live curve and sliders."""
    return [0.5 * math.sin(0.7 * t + 0.3), 0.3 * math.sin(0.9 * t + 1.1), 0.6 * math.sin(0.6 * t + 2.0),
            0.5 * math.sin(1.1 * t + 0.4), 0.35 * math.sin(0.8 * t + 2.6), 0.3 * math.sin(1.3 * t + 1.7)]


def b_math_kan(S):
    c, e = S.cue, S.cue_end
    out_all = c[5] - 0.25
    # intro + floating symbols
    S.add(T("Time for some maths", 76, "bold"), W / 2, 380, at=c[0] + 0.1, anim="pop", anchor="ma",
          out=c[1] - 0.1, sfx="pop")
    S.add(T("(it's friendlier than it looks)", 34, "regular", "muted"), W / 2, 490, at=c[0] + 1.2, anim="fade",
          anchor="ma", out=c[1] - 0.1)
    syms = [M(s, 60, (90, 120, 170)) for s in [r"\Sigma", r"\pi", r"x^2", r"\phi", r"\int", r"T_n", r"\sqrt{x}"]]

    def floaters(t):
        out = []
        for i, im in enumerate(syms):
            x = 200 + i * 240 + 40 * math.sin(t * 0.8 + i)
            y = 860 - ((t - c[0]) * 60 + i * 97) % 640
            out.append((im, x, y, 0.5))
        return out
    S.dyn(floaters, at=c[0], out=c[1] - 0.1)

    # left: weight -> curve demo
    lx, ly, lw, lh = X0, 180, 840, 420
    S.add(panel(lw, lh).img(), lx, ly, at=c[1], out=out_all)
    n1, n2 = (lx + 110, ly + 230), (lx + lw - 110, ly + 230)
    t_curve = at(S, 2, 0.3)
    node = Canvas(56, 56)
    node.circle(28, 28, 24, fill="panel2", outline="blue", width=4)
    node = node.img()
    labels = {}

    def demo(t):
        cv = Canvas(lw, lh, ss=2)
        a = ease(clamp01((t - t_curve) / 1.0))
        cf = coeffs(t)
        pts = []
        for i in range(61):
            u = i / 60
            xx = u * 2 - 1
            curve = cf[0] * xx + sum(cf[k + 1] * cheb(k, np.array(math.tanh(1.5 * xx))) for k in range(5))
            w = 0.9 * math.sin(t * 1.4)
            yv = (1 - a) * 0 + a * float(curve) * 70
            pts += [110 + (lw - 220) * u, 230 - yv]
        w = 0.9 * math.sin(t * 1.4)
        col = "teal" if (a > 0.5 or w >= 0) else "red"
        width = 4 + (1 - a) * 6 * abs(w)
        cv.line(pts, col if a < 0.5 else "amber", width)
        items = [(cv.img(), lx, ly)]
        items += [(node, n1[0] - 28, n1[1] - 28), (node, n2[0] - 28, n2[1] - 28)]
        if a < 0.5:
            s = f"w = {w:+.2f}"
            im = labels.get(s) or labels.setdefault(s, T(s, 34, "bold", col))
            items.append((im, lx + lw / 2 - im.width / 2, ly + 120))
        return items
    S.dyn(demo, at=c[1] + 0.1, out=out_all)
    S.add(T("Normal network: one number", 28, "semibold", "muted"), lx + 30, ly + 24, at=c[1] + 0.2,
          anim="fade", out=t_curve)
    S.add(M(r"y = w \cdot x", 40), lx + lw / 2, ly + 330, at=c[1] + 0.6, anchor="ma", out=t_curve)
    S.add(T("ChebyKAN: a whole curve", 28, "semibold", "amber"), lx + 30, ly + 24, at=t_curve, anim="fade",
          out=out_all)
    S.add(M(r"y = \phi(x)", 40, "amber"), lx + lw / 2, ly + 330, at=t_curve + 0.2, anchor="ma", out=out_all,
          sfx="pop")

    # right: Chebyshev polynomials drawn one by one
    rx, ry, rw, rh = 960, 180, X1 - 960, 420
    S.add(panel(rw, rh).img(), rx, ry, at=c[3], out=out_all)
    S.add(M(r"T_0 = 1,\quad T_1 = x", 34), rx + 30, ry + 20, at=c[3] + 0.2, out=out_all)
    S.add(M(r"T_{n+1} = 2x\,T_n - T_{n-1}", 34, "amber"), rx + 400, ry + 20, at=at(S, 3, 0.55), out=out_all,
          sfx="pop")
    px0, py0, pw, ph = 60, 110, rw - 100, 280
    axes = Canvas(rw, rh)
    axes.line([px0, py0 + ph / 2, px0 + pw, py0 + ph / 2], "border", 2)
    axes.line([px0 + pw / 2, py0, px0 + pw / 2, py0 + ph], "border", 2)
    axes.text(px0 + pw + 6, py0 + ph / 2, "x", 20, "italic", "muted", anchor="lm")
    S.add(axes.img(), rx, ry, at=c[3] + 0.3, anim="fade", out=out_all)
    xs = np.linspace(-1, 1, 160)
    curves = []
    for k in range(5):
        ys = cheb(k, xs)
        pts = [(rx + px0 + (x + 1) / 2 * pw, ry + py0 + ph / 2 - y * ph * 0.45) for x, y in zip(xs, ys)]
        curves.append(pts)
    t_draw = [at(S, 3, 0.25), at(S, 3, 0.32), at(S, 3, 0.6), at(S, 3, 0.72), at(S, 3, 0.84)]
    drawn = {}

    def cheb_draw(t):
        out = []
        for k, pts in enumerate(curves):
            p = clamp01((t - t_draw[k]) / 0.9)
            if p <= 0:
                continue
            key = (k, int(p * 30))
            im = drawn.get(key)
            if im is None:
                n = max(2, int(len(pts) * key[1] / 30))
                cv = Canvas(rw, rh, ss=2)
                flat = [v - o for pt in pts[:n] for v, o in zip(pt, (rx, ry))]
                cv.line(flat, hexrgb(SERIES[k]), 4)
                im = drawn[key] = cv.img()
            out.append((im, rx, ry))
        return out
    S.dyn(cheb_draw, at=t_draw[0], out=out_all)
    for k in range(5):
        lab = hstack([_sq(SERIES[k]), M(r"T_%d" % k, 26)], gap=6)
        S.add(lab, rx + 60 + k * 150, ry + rh - 44, at=t_draw[k], anim="pop", out=out_all)

    # bottom: the edge function with live sliders
    bx, by, bw, bh = X0, 630, CW, 280
    S.add(panel(bw, bh, fill="panel2", border="amber").img(), bx, by, at=c[4], out=out_all)
    S.add(M(r"\phi(x) = w_b\,x + \sum_{k=0}^{4} c_k\,T_k(\tanh x)", 46), bx + 40, by + 20, at=c[4] + 0.1,
          out=out_all, sfx="pop")
    names = ["w_b", "c_0", "c_1", "c_2", "c_3", "c_4"]
    name_imgs = [M(n, 28, "muted") for n in names]
    sl_x0, sl_y = bx + 60, by + 200
    knob = Canvas(26, 26)
    knob.circle(13, 13, 11, fill="amber", outline="text", width=2)
    knob = knob.img()
    track = Canvas(160, 8)
    track.rrect(0, 0, 159, 7, r=4, fill="border")
    track = track.img()

    def sliders(t):
        cf = coeffs(t)
        out = []
        for i in range(6):
            x = sl_x0 + i * 200
            out.append((track, x, sl_y))
            out.append((knob, x + 80 + cf[i] / 0.65 * 70 - 13, sl_y - 9))
            out.append((name_imgs[i], x + 80 - name_imgs[i].width / 2, sl_y + 18))
        return out
    S.dyn(sliders, at=at(S, 4, 0.3), out=out_all)
    S.add(pill("6 numbers per connection", "amber", 26, filled=True), X1 - 40, by + 190, at=at(S, 4, 0.8),
          anim="pop", anchor="ra", out=out_all, sfx="pop")

    # finale: network + counter
    net = Canvas(980, 600)
    cols = [(90, 7, "blue"), (380, 8, "teal"), (670, 8, "teal"), (900, 4, "amber")]
    pos = []
    for x, n, col in cols:
        span = 58 * (n - 1)
        pos.append([(x, 300 - span / 2 + i * 58) for i in range(n)])
    edges = []
    for A, B in zip(pos, pos[1:]):
        for a in A:
            for b in B:
                net.line([*a, *b], (90, 120, 170, 60), 1.6)
                edges.append((a, b))
    for (x, n, col), P in zip(cols, pos):
        for (xx, yy) in P:
            net.circle(xx, yy, 14, fill="panel2", outline=col, width=3)
    for (x, _, _), lab in zip(cols, ["46 in", "64", "64", "4 out"]):
        net.text(x, 560, lab, 24, "semibold", "muted", anchor="mm")
    nx, ny = X0, 220
    S.add(net.img(), nx, ny, at=c[5], anim="fade")
    dot = Canvas(14, 14)
    dot.circle(7, 7, 6, fill="amber")
    dot = dot.img()
    rng = np.random.default_rng(11)
    picks = [edges[i] for i in rng.choice(len(edges), 40, replace=False)]

    def pulses(t):
        out = []
        for i, (a, b) in enumerate(picks):
            p = ((t - c[5]) / 1.2 + i / 40) % 1.0
            out.append((dot, nx + lerp(a[0], b[0], p) - 7, ny + lerp(a[1], b[1], p) - 7))
        return out
    S.dyn(pulses, at=c[5] + 0.3)
    S.counter(1150, 300, c[5] + 0.3, at(S, 5, 0.6), 0, 44164, size=120, color="teal")
    S.add(T("learnable numbers per car", 30, "semibold", "muted"), 1150, 450, at=c[5] + 0.5, anim="fade")
    S.add(T("7,296 connections × 6  +  388 bias & norm terms", 22, "regular", "dim"), 1150, 500,
          at=c[5] + 0.8, anim="fade")
    for i in range(8):
        S.add(icon_lock(46, "amber"), 1160 + i * 70, 580, at=at(S, 5, 0.7) + 0.08 * i, anim="pop",
              sfx="click" if i == 0 else None)
    S.add(T("…and every one gets encrypted", 26, "semibold", "amber"), 1150, 650, at=at(S, 5, 0.75),
          anim="fade")


# =================================================================== math: CKKS
def train(n_seats=32, w=1500, h=110, filled=0, label=None):
    s = h / 110
    cv = Canvas(w, h + 30 * s)
    eng = 150 * s
    cv.rrect(0, 20 * s, eng, h + 10 * s, r=18 * s, fill="amber")
    cv.rect(eng - 50 * s, 0, eng - 20 * s, 28 * s, fill="amber")
    if label:
        cv.text(eng / 2, h / 2 + 18 * s, label, max(10, int(26 * s)), "bold", "bg0", anchor="mm")
    cv.rrect(eng + 10 * s, 20 * s, w - 2, h + 10 * s, r=14 * s, fill="panel2", outline="teal", width=max(2, 3 * s))
    sw = (w - eng - 30 * s) / n_seats
    for i in range(n_seats):
        x = eng + 20 * s + i * sw
        cv.rrect(x + 2 * s, 34 * s, x + sw - 3 * s, h - 4 * s, r=5 * s,
                 fill=alpha("teal", 150) if i < filled else alpha("teal", 35))
    for cx in [eng * 0.3, eng * 0.75] + [eng + 60 * s + k * (w - eng - 80 * s) / 5 for k in range(6)]:
        cv.circle(cx, h + 14 * s, 13 * s, fill="bg0", outline="muted", width=max(2, 3 * s))
    return cv.img()


def b_math_ckks(S):
    c, e = S.cue, S.cue_end
    outA, outB = c[2] - 0.25, c[5] - 0.25
    # A: one train
    tr = train(32, 1500, 110, 0, "ct")
    S.move(tr, [(W + 900, 330), (X0 + 750 + 80, 330)], c[0] + 0.2, c[0] + 1.6, ease_fn=ease, out=outA,
           sfx="whoosh")
    seat_w = (1500 - 150 - 30) / 32
    seat = Canvas(int(seat_w) - 8, 50)
    seat.rrect(0, 0, int(seat_w) - 9, 49, r=6, fill="teal")
    seat = seat.img()
    t_fill = c[0] + 1.8

    def fill_seats(t):
        out = []
        for i in range(32):
            p = clamp01((t - t_fill - i * 0.06) / 0.35)
            if p > 0:
                x = X0 + 80 + 150 + 20 + i * seat_w + 2
                y = 330 - 55 + 34 - 30 * (1 - ease(p))
                out.append((seat, x, y, p))
        return out
    S.dyn(fill_seats, at=t_fill, out=outA)
    S.add(T("one ciphertext  =  4,096 seats (slots)", 32, "bold"), X0, 200, at=at(S, 0, 0.6), anim="fade",
          out=outA)
    S.add(M(r"N = 8192 \;\Rightarrow\; N/2 = 4096\ \mathrm{slots}", 36, "muted"), X0, 450, at=at(S, 0, 0.75),
          out=outA)
    w_ex = 0.0183
    S.add(M(r"w = 0.0183 \;\rightarrow\; \lfloor 0.0183 \cdot 2^{40} \rceil = %s"
            % f"{round(w_ex * 2 ** 40):,}".replace(",", r"{,}"), 34, "amber"), X0, 520, at=c[1] + 0.2,
          out=outA, sfx="pop")
    # eleven small trains
    small = [train(8, 150, 40, 8 if i < 10 else 6, None) for i in range(11)]
    for i, im in enumerate(small):
        t0 = at(S, 1, 0.35) + 0.12 * i
        x = X0 + i * 160 + im.width / 2
        S.move(im, [(W + 300, 690), (x, 690)], t0, t0 + 0.8, ease_fn=ease, out=outA)
    S.add(T("44,164 weights  →  11 trains", 30, "bold", "teal"), X0, 760, at=at(S, 1, 0.6), anim="fade",
          out=outA)
    S.add(T("last one: 3,204 + 892 empty seats", 24, "semibold", "muted"), X1, 770, at=at(S, 1, 0.8),
          anim="fade", anchor="ra", out=outA)

    # B: function F with locked boxes
    ns = ["1,200", "800", "2,000"]
    by = [400, 540, 680]
    steps = [at(S, 2, 0.25), at(S, 2, 0.5), at(S, 2, 0.78)]
    S.add(T("example sample counts", 18, "regular", "dim"), X0 + 20, 760, at=c[2] + 0.4, anim="fade", out=outB)
    for i, y in enumerate(by):
        S.add(icon_car(80, "blue"), X0 + 20, y - 20, at=c[2] + 0.1 * i, anim="pop", out=outB)
        S.add(box_locked(70), X0 + 230, y, at=c[2] + 0.2 + 0.1 * i, anim="pop", anchor="mm", out=steps[1])
        S.add(T(f"× {ns[i]}", 28, "bold", "amber"), X0 + 280, y - 16, at=steps[0] + 0.1 * i, anim="pop",
              out=steps[1], sfx="pop" if i == 0 else None)
        S.move(box_locked(70), [(X0 + 230, y), (760, 540)], steps[1], steps[1] + 0.6, at=steps[1],
               out=steps[1] + 0.6)
    S.add(box_locked(110, label="Σ"), 760, 540, at=steps[1] + 0.55, anim="pop", anchor="mm", out=outB,
          sfx="pop")
    S.add(T("× 1/N", 34, "bold", "amber"), 840, 500, at=steps[2], anim="pop", out=outB)
    arr = Canvas(220, 40)
    arr.arrow(0, 20, 210, 20, color="muted", width=5, head=18)
    S.add(arr.img(), 940, 520, at=steps[2] + 0.2, anim="wipe", out=outB)
    S.add(box_locked(110, label="F"), 1240, 540, at=steps[2] + 0.5, anim="pop", anchor="mm", out=outB,
          sfx="pop")
    S.add(M(r"\tilde{c}_k = n_k \odot c_k", 38), X0, 196, at=steps[0], out=outB)
    S.add(M(r"c_{\mathrm{sum}} = \Sigma_k\, \tilde{c}_k", 38), 640, 196, at=steps[1], out=outB)
    S.add(M(r"c_F = \frac{1}{N} \odot c_{\mathrm{sum}}", 38), 1180, 190, at=steps[2], out=outB)
    S.add(pill("plain × locked  →  cheap, depth 0", "green", 24), X0, 290, at=c[3] + 0.2, anim="pop", out=outB,
          sfx="pop")
    S.add(crossed(pill("locked × locked  →  not needed", "red", 24), strike=True), 760, 290, at=at(S, 3, 0.6),
          anim="pop", out=outB)
    # unlock the sum: same numbers
    ux = 1400
    S.add(box_locked(90, "teal", label="F", opened=True), ux + 120, 440, at=c[4] + 0.2, anim="pop",
          anchor="mm", out=outB, sfx="click")
    S.add(T("without encryption", 22, "semibold", "muted"), ux, 520, at=c[4] + 0.5, anim="fade", out=outB)
    t_roll0, t_roll1 = c[4] + 0.6, at(S, 4, 0.75)
    S.counter(ux, 552, t_roll0, t_roll1, 0, 0.4183127, fmt="{:.7f}", size=46, out=outB)
    S.add(T("with CKKS", 22, "semibold", "teal"), ux, 630, at=c[4] + 0.6, anim="fade", out=outB)
    S.counter(ux, 662, t_roll0, t_roll1, 0, 0.4183130, fmt="{:.7f}", size=46, color="teal", out=outB)
    S.add(T("example weight  ·  difference ≈ 10⁻⁷", 20, "regular", "dim"), ux, 730, at=at(S, 4, 0.8),
          anim="fade", out=outB, sfx="ding")
    S.add(M(r"\mathrm{Dec}(c_F) = \Sigma_k\,\frac{n_k}{N}\,\mathrm{Dec}(c_k)", 36), X0 + 320, 820,
          at=at(S, 4, 0.45), out=outB)

    # C: robustness — distance from the group
    rng = np.random.default_rng(4)
    pts = [(560 + rng.normal(0, 55), 520 + rng.normal(0, 55)) for _ in range(9)]
    outlier = (1000, 300)
    g = (560, 520)
    dotc = Canvas(26, 26)
    dotc.circle(13, 13, 11, fill="teal")
    dotc = dotc.img()
    dotr = Canvas(30, 30)
    dotr.circle(15, 15, 13, fill="red")
    dotr = dotr.img()
    t_c = c[5]
    t_lines = at(S, 5, 0.35)
    t_down = at(S, 5, 0.7)

    def scatter(t):
        out = []
        cv = Canvas(1100, 760, ss=1)
        if t > t_lines:
            for p in pts + [outlier]:
                cv.line([g[0] - X0, g[1] - 170, p[0] - X0, p[1] - 170],
                        alpha("red" if p == outlier else "muted", 160), 2 if p != outlier else 4)
        out.append((cv.img(), X0, 170))
        for p in pts:
            out.append((dotc, p[0] - 13, p[1] - 13))
        k = 1 - 0.6 * ease(clamp01((t - t_down) / 0.8))
        im = dotr.resize((max(4, int(30 * k)), max(4, int(30 * k))))
        out.append((im, outlier[0] - im.width / 2, outlier[1] - im.height / 2, 0.4 + 0.6 * k))
        return out
    S.dyn(scatter, at=t_c + 0.2)
    S.add(M(r"g", 40, "amber"), g[0] - 12, g[1] - 70, at=t_c + 0.4, anim="pop")
    S.add(T("the group", 22, "semibold", "muted"), 420, 700, at=t_c + 0.5, anim="fade")
    S.add(T("poisoned?", 24, "bold", "red"), outlier[0] + 30, outlier[1] - 20, at=t_c + 0.6, anim="pop",
          sfx="alert")
    S.add(M(r"d_k = \Vert w_k - g\Vert^2", 40), 1220, 220, at=t_lines)
    S.add(T("measured on locked updates", 20, "regular", "muted"), 1220, 290, at=t_lines + 0.3, anim="fade")
    S.add(M(r"p_k = 1 - \frac{d_k}{\Sigma_j\, d_j}", 40), 1220, 340, at=t_down - 0.4)
    S.add(T("trust weight per car", 20, "regular", "muted"), 1220, 430, at=t_down - 0.1, anim="fade")
    trust = [0.95, 0.94, 0.96, 0.93, 0.95, 0.94, 0.96, 0.95, 0.94, 0.45]
    for i, v in enumerate(trust):
        bar = Canvas(40, 200)
        h = v * 190
        bar.rrect(0, 200 - h, 39, 199, r=6, fill="red" if i == 9 else "teal")
        S.add(bar.img(), 1220 + i * 58, 480, at=t_down + 0.05 * i, anim="up",
              sfx="ding" if i == 9 else None)
    S.add(T("far away  →  trusted less", 22, "semibold", "red"), 1220, 700, at=t_down + 0.8, anim="fade")


# =================================================================== results
def b_results(S):
    c, e = S.cue, S.cue_end
    S.add(T("Does encryption hurt accuracy?", 60, "bold"), W / 2, 190, at=c[0] + 0.1, anim="pop",
          anchor="ma", out=c[1] - 0.1, sfx="pop")
    qm = T("?", 260, "black", "amber")

    def bob(t):
        return [(qm, W / 2 - qm.width / 2, 330 + 14 * math.sin(t * 3))]
    S.dyn(bob, at=c[0] + 0.5, out=c[1] - 0.1)
    S.pulse(W / 2, 500, 150, "amber", at=c[0] + 0.6, out=c[1] - 0.1)
    S.add(Image.new("RGBA", (1, 1)), 0, 0, at=e[0] + 0.2, sfx="rise")

    S.add(T("Nope.", 84, "black", "green"), X0, 170, at=c[1], anim="pop", sfx="ding")
    S.add(T("Encryption costs no accuracy", 40, "bold"), X0 + 280, 196, at=c[1] + 0.4, anim="fade")
    # racing bars on a full 0–100 % axis
    ax0, ax1, top = X0 + 330, X1 - 160, 300
    rows = [("Car-Hacking", "CKKS encrypted", 99.77, "teal"), ("", "plaintext", 99.81, "dim"),
            ("CICIDS-2017", "CKKS encrypted", 95.55, "teal"), ("", "plaintext", 95.42, "dim")]
    grid = Canvas(CW, 330)
    for k in range(0, 101, 25):
        x = ax0 - X0 + (ax1 - ax0) * k / 100
        grid.line([x, 0, x, 300], (46, 66, 100, 120), 2)
        grid.text(x, 318, f"{k} %", 18, "regular", "dim", anchor="mm")
    S.add(grid.img(), X0, top - 10, at=c[1] + 0.3, anim="fade")
    t_race = at(S, 1, 0.2)
    bar_imgs = []
    for i, (ds, lab, v, col) in enumerate(rows):
        y = top + i * 72 + (20 if i >= 2 else 0)
        if ds:
            S.add(T(ds, 26, "bold"), X0, y + 4, at=c[1] + 0.3, anim="fade")
        S.add(T(lab, 20, "regular", "muted"), X0 + 180, y + 10, at=c[1] + 0.3, anim="fade")
        b = Canvas(ax1 - ax0, 44)
        b.rrect(0, 0, (ax1 - ax0) * v / 100, 43, r=8, fill=col)
        bar_imgs.append((b.img(), y, v, i))

    def race(t):
        out = []
        for im, y, v, i in bar_imgs:
            p = ease(clamp01((t - t_race - 0.15 * i) / 1.6))
            w = max(1, int(im.width * p))
            out.append((im.crop((0, 0, w, im.height)), ax0, y))
        return out
    S.dyn(race, at=t_race)
    for im, y, v, i in bar_imgs:
        S.counter(ax1 + 14, y + 4, t_race + 0.15 * i, t_race + 0.15 * i + 1.6, 0, v, fmt="{:.2f} %", size=30,
                  at=t_race + 0.15 * i)
    S.add(T("gap 0.04 points  <  run-to-run noise (±0.12)   ·   3 seeds, 10 cars, 5 rounds", 21, "semibold",
            "muted"), X0, 640, at=at(S, 1, 0.75), anim="fade")

    tw = (CW - 40) // 3
    ty = 690
    t1 = panel(tw, 220)
    t1.paste(T("encryption error", 24, "semibold", "muted"), 26, 20)
    t1.paste(T("< 1 in a million", 46, "bold"), 26, 66)
    t1.paste(T("measured 8.2 × 10⁻⁷", 22, "regular", "muted"), 26, 140)
    S.add(t1.img(), X0, ty, at=c[2] + 0.2, anim="pop", sfx="pop")
    t2 = panel(tw, 220)
    t2.paste(T("updates the server decrypted", 24, "semibold", "muted"), 26, 20)
    t2.paste(icon_shield(70, "green"), tw - 100, 70)
    t2.paste(T("individual car updates, in every run", 22, "regular", "muted", maxw=tw - 140), 26, 150)
    S.add(t2.img(), X0 + tw + 20, ty, at=at(S, 2, 0.5), anim="pop")
    S.counter(X0 + tw + 46, ty + 56, at(S, 2, 0.5), at(S, 2, 0.5) + 0.01, 0, 0, size=72, color="green",
              sfx="ding")
    t3 = panel(tw, 220, border="amber")
    t3.paste(T("the price: bandwidth", 24, "semibold", "amber"), 26, 20)
    t3.paste(T("≈ 21× bigger  ·  V2X frames are ~2.7 KB", 20, "regular", "muted", maxw=tw - 52), 26, 170)
    S.add(t3.img(), X0 + 2 * (tw + 20), ty, at=c[3] + 0.1, anim="pop", sfx="pop")
    fi = doc_icon(70)
    t_inf = at(S, 3, 0.25)

    def inflate(t):
        k = 0.45 + 0.75 * back_out(clamp01((t - t_inf) / 1.2))
        im = fi.resize((max(4, int(fi.width * k)), max(4, int(fi.height * k))))
        cx, cy = X0 + 2 * (tw + 20) + tw - 90, ty + 105
        return [(im, cx - im.width / 2, cy - im.height / 2)]
    S.dyn(inflate, at=c[3] + 0.3)
    S.counter(X0 + 2 * (tw + 20) + 26, ty + 70, t_inf, t_inf + 1.4, 0.17, 3.5, fmt="{:.2f} MB", size=50)
    S.add(pill("work in progress", "amber", 20, filled=True), X1 - 20, ty - 20, at=at(S, 3, 0.75), anim="pop",
          anchor="ra")


# =================================================================== status
def b_status(S):
    c, e = S.cue, S.cue_end
    # mini timeline with a sliding "we are here" marker
    ms = ["Months 1–4", "Month 5", "Aug–Oct", "multi-key", "hardware"]
    tl = Canvas(CW, 90)
    xs = [120 + i * (CW - 240) / 4 for i in range(5)]
    tl.line([xs[0], 30, xs[-1], 30], "border", 4)
    tl.line([xs[0], 30, xs[2], 30], "green", 4)
    for i, (x, m) in enumerate(zip(xs, ms)):
        tl.circle(x, 30, 11, fill="green" if i < 3 else "panel2", outline="green" if i < 3 else "muted", width=3)
        tl.text(x, 70, m, 19, "semibold", "text" if i < 3 else "muted", anchor="mm")
    S.add(tl.img(), X0, 158, at=c[0], anim="wipe", dur=1.0)
    here = pill("we are here", "amber", 18, filled=True)

    def marker(t):
        p = ease(clamp01((t - c[0] - 0.4) / 1.4))
        x = X0 + lerp(xs[0], (xs[2] + xs[3]) / 2, p)
        return [(here, x - here.width / 2, 150 - here.height)]
    S.dyn(marker, at=c[0] + 0.3)

    # done checklist
    done = panel(600, 600)
    done.paste(T("Done", 34, "bold", "green"), 30, 22)
    S.add(done.img(), X0, 290, at=c[0] + 0.2)
    items = ["Encrypted federated pipeline", "Function F + proof", "Encrypted robust weighting",
             "Packing: −29.6 % bandwidth", "NTT reference: 11.2× faster", "Conference paper draft"]
    for i, it in enumerate(items):
        t0 = at(S, 0, 0.2) + 0.45 * i
        S.add(icon_status("good", 36), X0 + 30, 370 + i * 80, at=t0, anim="pop", sfx="click" if i < 3 else None)
        S.add(T(it, 25, "semibold"), X0 + 82, 372 + i * 80, at=t0 + 0.05, anim="left")

    # multi-key story
    rx = 720
    S.add(T("Next: multi-key encryption", 34, "bold", "amber"), rx, 296, at=c[1], anim="fade")
    cars_x = [rx + 120, rx + 520, rx + 920]
    for i, x in enumerate(cars_x):
        S.add(icon_car(150, "blue"), x, 420, at=c[1] + 0.2 + 0.1 * i, anim="pop", anchor="mm")
    t_one = at(S, 1, 0.55)
    t_split = c[2] + 0.2
    for i, x in enumerate(cars_x):
        S.add(icon_key(54, "amber"), x + 70, 380, at=t_one + 0.1 * i, anim="pop", out=t_split,
              sfx="pop" if i == 0 else None)
    S.add(T("today: everyone shares one key", 24, "semibold", "amber"), rx, 500, at=t_one + 0.3, anim="fade",
          out=t_split)
    piece_cols = ["teal", "violet", "green"]
    box_c = (rx + 520, 600)
    t_go = at(S, 2, 0.35)
    for i, x in enumerate(cars_x):
        S.add(icon_key(54, piece_cols[i]), x + 70, 380, at=t_split + 0.1 * i, anim="pop", out=t_go + 0.2 * i,
              sfx="pop" if i == 0 else None)
        S.move(icon_key(54, piece_cols[i]), [(x + 97, 407), (box_c[0] - 90 + 90 * i, box_c[1] - 70)],
               t_go + 0.2 * i, t_go + 0.2 * i + 0.9, at=t_go + 0.2 * i)
    S.add(T("each car holds one piece", 24, "semibold", "teal"), rx, 500, at=t_split + 0.4, anim="fade")
    t_open = t_go + 0.4 + 0.9 + 0.2
    S.add(box_locked(90), box_c[0], box_c[1] + 20, at=c[2] + 0.6, anim="pop", anchor="mm", out=t_open)
    S.add(box_locked(90, "teal", opened=True), box_c[0], box_c[1] + 20, at=t_open, anim="pop", anchor="mm",
          sfx="ding")
    S.add(T("all pieces together unlock it — no one can peek alone", 22, "semibold", "green"), box_c[0],
          box_c[1] + 80, at=t_open + 0.2, anim="fade", anchor="ma")
    mig = hstack([pill("TenSEAL", "dim", 24), T("→", 34, "bold", "teal"), pill("OpenFHE", "teal", 24, filled=True)],
                 gap=14)
    S.add(mig, rx + 1020, 296, at=c[3] + 0.2, anim="pop", anchor="ra", sfx="pop")

    # hardware
    hw = panel(X1 - rx, 190, border="teal")
    hw.paste(icon_chip(80, "teal"), 30, 30)
    hw.paste(T("Then: hardware", 30, "bold", "teal"), 130, 30)
    hw.paste(T("NXP S32G board  ·  Raspberry Pi 5  ·  NEON-accelerated NTT  ·  on-vehicle IDS", 21, "regular",
               "text", maxw=X1 - rx - 160), 130, 84)
    S.add(hw.img(), rx, 720, at=c[4] + 0.1, anim="up", sfx="pop")
    car = icon_car(120, "blue")
    lines = Canvas(80, 40)
    for k in range(3):
        lines.line([0, 8 + k * 12, 60 - k * 12, 8 + k * 12], "teal", 3)
    lines = lines.img()

    def drive(t):
        x = X1 - 200 + 10 * math.sin(t * 6)
        return [(lines, x - 90, 830), (car, x, 812), (icon_chip(36, "amber"), x + 50, 800)]
    S.dyn(drive, at=at(S, 4, 0.6))


# =================================================================== summary
def b_summary(S):
    c, e = S.cue, S.cue_end
    cx, cy = W / 2, 360
    car = car7(300)
    leave = c[1] + 0.3

    def hero(t):
        x = cx if t < leave else cx + (t - leave) ** 2 * 900
        return [(car, x - car.width / 2, cy - car.height / 2)]
    S.dyn(hero, at=0.2)
    ring = [(-460, -60), (-330, 120), (330, 120), (460, -60), (-200, -170), (200, -170)]
    for i, (dx, dy) in enumerate(ring):
        S.add(icon_car(110, "blue"), cx + dx, cy + dy, at=0.3 + 0.1 * i, anim="pop", anchor="mm", out=leave)
    pills = [("learns from the whole fleet", "blue", at(S, 0, 0.15)), ("server computes blind", "violet", at(S, 0, 0.45)),
             ("privacy costs no accuracy", "green", at(S, 0, 0.75))]
    xs = [W / 2 - 560, W / 2, W / 2 + 560]
    for (txt, col, t0), x in zip(pills, xs):
        S.add(pill(txt, col, 28, filled=True), x, 600, at=t0, anim="pop", anchor="ma", sfx="pop")
    S.add(T("Thanks for riding along!", 72, "bold"), W / 2, 720, at=c[1], anim="pop", anchor="ma", sfx="ding")


BUILDERS = dict(title=b_title, problem=b_problem, idea=b_idea, data=b_data, attacks=b_attacks,
                math_kan=b_math_kan, math_ckks=b_math_ckks, results=b_results, status=b_status,
                summary=b_summary)

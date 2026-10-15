"""Visual builders, one per narration scene.

Every builder receives a ``SceneBuild`` whose ``cue[i]`` is the time (seconds,
relative to the scene start) at which sentence ``i`` of that scene begins.
Elements are positioned in absolute 1920x1080 frame coordinates.
Content area: x 80..1840, y 180..900 (header above, captions below).
"""
from __future__ import annotations

import math

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

from engine import (C, SERIES, W, Canvas, alpha, card, fig_to_img, hstack, icon_car, icon_chip,
                    icon_key, icon_lock, icon_server, icon_shield, icon_status, icon_tower,
                    math_img, pill, rgba, text_img, vstack)

X0, X1, Y0, Y1 = 80, 1840, 180, 900
CW = X1 - X0


def T(s, size=26, kind="regular", color="text", **kw):
    return text_img(s, size, kind, color, **kw)


def M(tex, size=44, color="text"):
    return math_img(tex, size, color)


def status_row(kind, label, detail=None, w=560, label_size=24, detail_size=20):
    ic = icon_status(kind, 30)
    txt = [T(label, label_size, "semibold", "text", maxw=w - 50)]
    if detail:
        txt.append(T(detail, detail_size, "regular", "muted", maxw=w - 50))
    col = vstack(txt, gap=2)
    out = Image.new("RGBA", (w, max(col.height, 34)), (0, 0, 0, 0))
    out.alpha_composite(ic, (0, 3))
    out.alpha_composite(col, (46, 0))
    return out


def panel(w, h, fill="panel", border="border", r=18):
    cv = Canvas(w, h)
    cv.rrect(0, 0, w - 1, h - 1, r=r, fill=fill, outline=border, width=2)
    return cv


# =================================================================== title
def b_title(S):
    c = S.cue
    k = T("LG SOFT INDIA  ·  12-MONTH INDUSTRY RESEARCH PROJECT", 24, "semibold", "teal", tracking=3)
    S.add(k, W / 2, 230, at=0.3, anchor="ma", anim="fade")
    S.add(T("Privacy-Preserving Collaborative", 80, "bold"), W / 2, 280, at=0.5, anchor="ma")
    S.add(T("Intrusion Detection for the Internet of Vehicles", 58, "semibold"), W / 2, 392,
          at=0.8, anchor="ma")

    cv = Canvas(860, 215)
    cv.paste(icon_car(220, "blue"), 0, 50)
    cv.arrow(250, 105, 600, 105, color="teal", width=5, head=20, dashed=True)
    cv.paste(icon_lock(54, "amber"), 400, 38)
    cv.paste(T("encrypted update", 22, "regular", "muted"), 425, 125, anchor="ma")
    cv.paste(icon_server(110, 150, "violet"), 640, 20)
    cv.paste(T("server computes blind", 22, "regular", "muted"), 695, 180, anchor="ma")
    S.add(cv.img(), W / 2, 510, at=c[0] + 1.2, anchor="ma", anim="fade")

    tags = hstack([pill("Federated Learning", "blue"), pill("CKKS Homomorphic Encryption", "amber"),
                   pill("ChebyKAN", "teal"), pill("Byzantine-robust aggregation", "violet")], gap=18)
    S.add(tags, W / 2, 770, at=c[1], anchor="ma")
    S.add(T("Project status as of October 2026", 22, "regular", "dim"), W / 2, 860, at=c[1] + 0.6,
          anchor="ma", anim="fade")


# =================================================================== problem
_BUS_Y = 380
_ECU_X = [150, 365, 580, 795]


def b_problem(S):
    c = S.cue
    px, py, pw, ph = X0, 190, 940, 690
    cv = panel(pw, ph)
    cv.text(28, 22, "Inside every vehicle", 28, "semibold", "muted")
    cv.line([50, _BUS_Y, 900, _BUS_Y], (88, 118, 168), 10)
    cv.text(50, _BUS_Y - 44, "CAN bus", 24, "semibold", (120, 150, 200))
    top = ["Engine", "Brakes", "Steering", "Airbag"]
    bot = ["Gearbox", "Dashboard", "Infotainment"]
    for x, name in zip(_ECU_X, top):
        cv.line([x, 250, x, _BUS_Y], (88, 118, 168), 4)
        cv.rrect(x - 85, 170, x + 85, 250, r=14, fill="panel2", outline="blue", width=2)
        cv.text(x, 210, name, 24, "semibold", "text", anchor="mm")
    for x, name in zip(_ECU_X, bot):
        cv.line([x, _BUS_Y, x, 510], (88, 118, 168), 4)
        cv.rrect(x - 85, 510, x + 85, 590, r=14, fill="panel2", outline="blue", width=2)
        cv.text(x, 550, name, 24, "semibold", "text", anchor="mm")
    cv.text(28, 640, "~70–100 electronic control units share one broadcast bus", 21, "regular", "dim")
    S.add(cv.img(), px, py, at=c[0] - 0.2)

    # attacker node
    a = Canvas(190, 230)
    a.line([95, 0, 95, 130], "red", 4)
    a.rrect(10, 130, 180, 210, r=14, fill=alpha("red", 50), outline="red", width=3)
    a.text(95, 158, "Compromised", 21, "semibold", "red", anchor="mm")
    a.text(95, 184, "node", 21, "semibold", "red", anchor="mm")
    S.add(a.img(), px + _ECU_X[3] - 95, py + _BUS_Y, at=c[1], anim="fade")
    S.add(pill("No authentication  ·  No encryption", "red", 22), px + pw - 24, py + 18, at=c[1] + 0.4,
          anchor="ra")

    pk_ok = Canvas(34, 18)
    pk_ok.rrect(0, 0, 33, 17, r=5, fill="teal")
    pk_bad = Canvas(34, 18)
    pk_bad.rrect(0, 0, 33, 17, r=5, fill="red")
    pk_ok, pk_bad = pk_ok.img(), pk_bad.img()
    attack_t = c[1] - (c[0] - 0.2)

    def packets(lt):
        out = []
        for i in range(8):
            x = (lt * 150 + i * 108) % 850 + 50
            bad = lt > attack_t and i % 2 == 1
            out.append((pk_bad if bad else pk_ok, px + x - 17, py + _BUS_Y - 9))
        return out

    S.dyn(packets, at=c[0] + 0.3)

    rx, rw = 1060, 780
    cards = [
        dict(title="2015 · Jeep Cherokee hacked remotely",
             body="Researchers reached the CAN bus over the infotainment's cellular link and disabled "
                  "the transmission on a highway. 1.4 million vehicles recalled.",
             accent="amber", icon=icon_status("warn", 30)),
        dict(title="Detection needs fleet-scale data",
             body="An IDS learns what normal CAN traffic looks like, across many cars, models and drivers.",
             accent="blue", icon=None),
        dict(title="Federated learning",
             body="Raw driving logs stay in each car. Only model updates are shared.",
             accent="teal", icon=icon_status("good", 30)),
        dict(title="…but updates leak",
             body="Gradient inversion reconstructs training data from an update. Goal: learn together "
                  "without exposing any single vehicle's update.",
             accent="red", icon=icon_status("bad", 30)),
    ]
    y = 190
    for i, cd in enumerate(cards):
        im = card(rw, 160, cd["title"], cd["body"], accent=cd["accent"], icon=cd["icon"],
                  title_size=27, body_size=22)
        S.add(im, rx, y, at=c[2 + i], anim="right")
        y += 177


# =================================================================== approach
def b_approach(S):
    c = S.cue
    car_y = [235, 425, 615]
    S.add(T("Vehicles (clients)", 24, "semibold", "muted"), 90, 186, at=c[0] - 0.2, anim="fade")
    for i, y in enumerate(car_y):
        g = vstack([icon_car(170, "blue"),
                    T(f"Vehicle {i + 1}  ·  ChebyKAN on local CAN data", 19, "regular", "muted")], gap=4)
        S.add(g, 90, y, at=c[0] + 0.25 * i, anim="left")

    # encrypted uploads
    sx, sy, sw, sh = 820, 285, 420, 330
    for i, y in enumerate(car_y):
        S.add(icon_lock(44, "amber"), 275, y + 12, at=c[1] + 0.2 * i, anim="fade")
        y0 = y + 42
        y1 = sy + 90 + i * 75
        cv = Canvas(sx - 330, max(y0, y1) - min(y0, y1) + 60)
        top = min(y0, y1) - 30
        cv.arrow(0, y0 - top, sx - 340, y1 - top, color="amber", width=4, head=16, dashed=True)
        S.add(cv.img(), 330, top, at=c[1] + 0.2 * i + 0.2, anim="wipe", dur=0.8)
        lab = M(r"\mathrm{Enc}(\Delta w_%d)" % (i + 1), 28, "amber")
        y_line = y0 + (y1 - y0) * (480 - 330) / (sx - 330)
        S.add(lab, 480, y_line - 10, at=c[1] + 0.2 * i + 0.6, anim="fade", anchor="mb")

    sv = panel(sw, sh, fill="panel2", border="violet")
    sv.paste(icon_tower(90, "violet"), 24, 22)
    sv.text(130, 40, "Roadside unit / server", 26, "semibold", "text")
    sv.text(130, 76, "untrusted aggregator", 21, "regular", "muted")
    S.add(sv.img(), sx, sy, at=c[1] + 0.4)
    S.add(M(r"c_F = F(c_1,\,\ldots,\,c_K)", 40, "text"), sx + sw / 2, sy + 150, at=c[2], anchor="ma")
    S.add(pill("holds no secret key", "amber", 22), sx + sw / 2, sy + 240, at=c[2] + 1.6, anchor="ma")

    rb = card(sw, 150, "Robust weighting", "encrypted distance to consensus → trust weight; outliers "
              "are down-weighted", accent="green", icon=icon_shield(40, "green"), title_size=25,
              body_size=20)
    S.add(rb, sx, sy + sh + 24, at=c[3])

    # decrypt + broadcast back
    dx, dy = 1350, 340
    cv = Canvas(1350 - (sx + sw) + 10, 40)
    cv.arrow(0, 20, cv.w - 6, 20, color="teal", width=5, head=18)
    S.add(cv.img(), sx + sw + 4, dy + 90, at=c[4], anim="wipe", dur=0.6)
    dk = card(470, 200, "Decrypt only the aggregate", None, accent="teal", icon=icon_key(40, "teal"),
              title_size=26)
    dk_c = Canvas(470, 200)
    dk_c.paste(dk, 0, 0)
    dk_c.paste(M(r"\mathrm{Dec}_{sk}(c_F)\;\rightarrow\;w^{(t+1)}", 34, "text"), 34, 95)
    S.add(dk_c.img(), dx, dy, at=c[4] + 0.4)
    # return path: down from the decrypt card, under everything, back up to the vehicles
    ox, oy = 165, dy + 200
    back = Canvas(dx + 235 - ox + 10, 880 - oy + 10)
    back.poly_arrow([dx + 235 - ox, 5, dx + 235 - ox, 880 - oy, 10, 880 - oy, 10, 750 - oy],
                    color="teal", width=5, head=20)
    S.add(back.img(), ox, oy, at=c[4] + 1.0, anim="wipe_rl", dur=1.2)
    S.add(T("new global model returns to every vehicle  →  next round", 22, "semibold", "teal"),
          560, 838, at=c[4] + 1.8, anchor="ma", anim="fade")


# =================================================================== data
def b_data(S):
    c = S.cue
    datasets = [
        ("Car-Hacking (HCRL)", "In-vehicle CAN · 5 captures", "570 MB · ~17 M messages",
         ("Primary benchmark", "teal")),
        ("CAN-VTC (IEEE)", "In-vehicle CAN · 4 captures", "228 MB · ~4.6 M messages",
         ("Flood detection only", "amber")),
        ("VeReMi", "V2X beacons · 19 attack types", "6.9 GB · ~24 M receptions",
         ("Needs sender IDs", "red")),
        ("CICIDS-2017", "Enterprise IP flows", "909 MB · ~2.8 M flows", ("Sanity check", "violet")),
    ]
    cw, gap = (CW - 3 * 20) // 4, 20
    for i, (name, kind, size, (role, rc)) in enumerate(datasets):
        cv = panel(cw, 190)
        cv.paste(T(name, 27, "semibold"), 22, 16)
        cv.paste(T(kind, 21, "regular", "muted"), 22, 58)
        cv.paste(T(size, 23, "semibold", "text"), 22, 92)
        x = X0 + i * (cw + gap)
        S.add(cv.img(), x, 190, at=c[0] + 0.15 * i)
        S.add(pill(role, rc, 19), x + 22, 330, at=c[1] + 0.3 * i, anim="fade")
    S.add(pill("8.6 GB total", "teal", 22, filled=True), X1, 92, at=c[0] + 0.8, anchor="ra", anim="fade")

    # message strip with per-message labels
    rng = np.random.default_rng(7)
    n, cell, g = 40, 22, 3
    inj = rng.random(n) < 0.22
    st = Canvas(n * (cell + g) + 10, 70)
    for i in range(n):
        x = i * (cell + g)
        st.rrect(x, 8, x + cell, 50, r=4, fill="red" if inj[i] else (70, 92, 128))
        st.text(x + cell / 2, 64, "T" if inj[i] else "R", 13, "monob", "red" if inj[i] else "muted",
                anchor="mm")
    S.add(T("CAN stream — every message keeps its own label (R = regular, T = injected)", 21, "regular",
            "muted"), X0, 402, at=c[2], anim="fade")
    S.add(st.img(), X0, 436, at=c[2] + 0.2, anim="wipe", dur=1.0)

    # sliding window (dynamic)
    win_cells, stride_cells = 12, 3
    br = Canvas(win_cells * (cell + g) + 6, 52)
    br.rrect(1, 1, br.w - 2, 50, r=6, outline="amber", width=4)
    br = br.img()

    def window(lt):
        k = int(lt / 0.7) % ((n - win_cells) // stride_cells + 1)
        return [(br, X0 - 4 + k * stride_cells * (cell + g), 439)]

    S.dyn(window, at=c[3])
    S.add(T("window = 64 messages, stride 16 (75 % overlap)", 21, "semibold", "amber"), X0, 512,
          at=c[3] + 0.2, anim="fade")

    # 46-feature bar
    fx, fw = 1150, X1 - 1150
    S.add(T("46 features per window", 24, "semibold"), fx, 398, at=c[3] + 0.8, anim="fade")
    segs = [(8, "byte means"), (8, "byte stds"), (2, "DLC"), (2, "ID ratio"), (24, "ID histogram"),
            (2, "entropy")]
    shades = [(57, 135, 229), (42, 120, 214), (85, 152, 231), (37, 106, 191), (28, 92, 171), (109, 167, 236)]
    fb = Canvas(fw, 110)
    x = 0
    for (k, lab), col in zip(segs, shades):
        wseg = fw * k / 46
        fb.rect(x + 1, 0, x + wseg - 1, 50, fill=col)
        if k >= 8:
            fb.text(x + wseg / 2, 25, str(k), 22, "bold", "text", anchor="mm")
        x += wseg
    fb.text(0, 64, "8 byte means · 8 byte stds · 2 DLC · 2 ID ratio / dominant ID ·", 18, "regular",
            "muted")
    fb.text(0, 88, "24 CAN-ID histogram buckets · 2 entropy / non-zero ratio", 18, "regular", "muted")
    S.add(fb.img(), fx, 436, at=c[3] + 1.0, anim="wipe", dur=0.9)
    arr = Canvas(40, 30)
    arr.arrow(0, 15, 36, 15, color="muted", width=4, head=14)
    S.add(arr.img(), 1100, 446, at=c[3] + 0.9, anim="fade")

    # block-disjoint split
    S.add(T("Block-disjoint split", 25, "semibold"), X0, 590, at=c[4], anim="fade")
    order = ["tr"] * 14 + ["va"] * 3 + ["te"] * 3
    rng.shuffle(order)
    colmap = {"tr": "teal", "va": "blue", "te": "amber"}
    bs = Canvas(860, 60)
    for i, o in enumerate(order):
        bs.rrect(i * 43, 0, i * 43 + 38, 52, r=6, fill=colmap[o])
    S.add(bs.img(), X0, 632, at=c[4] + 0.2, anim="wipe", dur=0.9)
    leg = hstack([status_like("teal", "70 % train"), status_like("blue", "15 % validation"),
                  status_like("amber", "15 % test")], gap=28)
    S.add(leg, X0, 700, at=c[4] + 0.6, anim="fade")
    S.add(T("A window never crosses a block, so overlapping windows cannot leak between splits.", 20,
            "regular", "muted", maxw=860), X0, 745, at=c[4] + 0.9, anim="fade")

    # clip/scale + Dirichlet fleet
    rx = 1000
    S.add(T("Clip at 0.5 / 99.5 percentiles  →  z-score (fitted on train only)", 22, "semibold",
            maxw=840), rx, 590, at=c[5], anim="fade")
    S.add(M(r"\mathrm{Dirichlet}(\alpha = 0.3)\;\rightarrow\;10\ \mathrm{vehicles}", 30, "text"), rx, 628,
          at=c[5] + 0.6, anim="fade")
    mix = rng.dirichlet([0.3] * 5, size=10)
    fl = Canvas(840, 200)
    bw = 52
    for v in range(10):
        x = v * 66
        y = 150
        for k in range(5):
            hgt = mix[v, k] * 140
            if hgt >= 1:
                fl.rect(x, y - hgt + 1, x + bw, y, fill=hex_rgb(SERIES[k]))
            y -= hgt
        fl.text(x + bw / 2, 172, f"V{v + 1}", 16, "semibold", "muted", anchor="mm")
    names = ["Normal", "DoS", "Fuzzy", "RPM", "Gear"]
    for k, nm in enumerate(names):
        fl.rect(690, 14 + k * 28, 706, 30 + k * 28, fill=hex_rgb(SERIES[k]))
        fl.text(716, 22 + k * 28, nm, 18, "regular", "text", anchor="lm")
    S.add(fl.img(), rx, 680, at=c[5] + 1.0, anim="wipe_tb", dur=0.8)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def status_like(color, label, size=20):
    sq = Canvas(18, 18)
    sq.rrect(0, 0, 17, 17, r=4, fill=color)
    return hstack([sq.img(), T(label, size, "regular", "text")], gap=8)


# =================================================================== attacks
def frame_strip(kind, n=12, seed=0):
    rng = np.random.default_rng(seed)
    normal_ids = ["0x316", "0x18F", "0x260", "0x2A0", "0x329", "0x545", "0x43F", "0x2C0", "0x370",
                  "0x4B1", "0x153", "0x220"]
    cv = Canvas(n * 40 + 4, 46)
    for i in range(n):
        x = i * 40
        bad = False
        lab = rng.choice(normal_ids)[2:]
        if kind == "dos" and i % 2 == 0:
            bad, lab = True, "000"
        elif kind == "fuzzy" and rng.random() < 0.35:
            bad, lab = True, f"{rng.integers(0, 0x7FF):03X}"
        elif kind in ("rpm", "gear") and i % 3 == 1:
            bad, lab = True, "RPM" if kind == "rpm" else "GR"
        cv.rrect(x, 0, x + 36, 44, r=6, fill=alpha("red", 70) if bad else (40, 58, 88),
                 outline="red" if bad else None, width=2)
        cv.text(x + 18, 22, lab, 13, "monob", "red" if bad else "muted", anchor="mm")
    return cv.img()


def b_attacks(S):
    c = S.cue
    attacks = [
        ("Denial of service", "Top-priority ID 0x000 floods the bus (24 % of frames).", "dos"),
        ("Fuzzy injection", "Random IDs and random payloads (13 % of frames).", "fuzzy"),
        ("RPM spoofing", "Fake engine-speed messages (19 % of frames).", "rpm"),
        ("Gear spoofing", "Fake gear-position messages (18.5 % of frames).", "gear"),
    ]
    cw, ch = 550, 262
    S.add(T("In-vehicle attacks  ·  Car-Hacking dataset", 22, "semibold", "muted"), X0, 186, at=c[0],
          anim="fade")
    for i, (title, body, kind) in enumerate(attacks):
        x = X0 + (i % 2) * (cw + 20)
        y = 226 + (i // 2) * (ch + 20)
        cv = panel(cw, ch)
        cv.paste(T(title, 28, "semibold"), 24, 20)
        cv.paste(T(body, 21, "regular", "muted", maxw=cw - 48), 24, 66)
        cv.paste(frame_strip(kind, seed=i), 24, ch - 84)
        cv.paste(T("illustrative frames · red = injected", 15, "regular", "dim"), 24, ch - 30)
        at = c[1] + 0.3 * i if i < 2 else c[2] + 0.3 * (i - 2)
        S.add(cv.img(), x, y, at=at)
    S.add(T("Percentages are measured injection rates in each capture. Every frame carries its own label, "
            "so the model learns injected traffic, not file names.", 19, "regular", "dim", maxw=1120),
          X0, 226 + 2 * ch + 40 + 4, at=c[2] + 1.0, anim="fade")

    rx, rw = 1220, X1 - 1220
    vc = panel(rw, 250)
    vc.paste(T("V2X misbehaviour  ·  VeReMi", 28, "semibold"), 24, 20)
    vc.paste(T("19 attack types, defined by how a sender's claims change over time", 21, "regular", "muted",
               maxw=rw - 48), 24, 64)
    chips = ["ConstPos", "RandomPos", "ConstSpeed", "DataReplay", "EventualStop", "DelayedMessages",
             "+13 more"]
    x, y = 24, 140
    for ch_ in chips:
        p = pill(ch_, "violet", 18, padx=12, pady=6)
        if x + p.width > rw - 20:
            x, y = 24, y + p.height + 10
        vc.paste(p, x, y)
        x += p.width + 10
    S.add(vc.img(), rx, 226, at=c[3], anim="right")

    lc = panel(rw, 392)
    lc.paste(T("Attacks on the learning itself", 28, "semibold"), 24, 18)
    rows = [("good", "Gradient inversion", "blocked: updates are CKKS-encrypted"),
            ("good", "Label flipping, model poisoning", "encrypted distance weighting"),
            ("partial", "Replay of old updates", "AES-GCM; round binding pending"),
            ("bad", "Low-magnitude persistent poisoning", "open problem, experiment planned")]
    y = 68
    for k, lab, det in rows:
        r = status_row(k, lab, det, w=rw - 48, label_size=22, detail_size=19)
        lc.paste(r, 24, y)
        y += r.height + 10
    S.add(lc.img(), rx, 492, at=c[4], anim="right")


# =================================================================== math: ChebyKAN
def cheb_plot():
    x = np.linspace(-1, 1, 400)
    Ts = [np.ones_like(x), x]
    for _ in range(3):
        Ts.append(2 * x * Ts[-1] - Ts[-2])
    fig, ax = plt.subplots(figsize=(8.6, 4.1), dpi=100)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    for k, (y, col) in enumerate(zip(Ts, SERIES)):
        ax.plot(x, y, color=col, lw=2.6, label=f"$T_{k}$", solid_capstyle="round")
    tc = np.array(C["muted"]) / 255
    for s in ax.spines.values():
        s.set_color(np.array(C["border"]) / 255)
    ax.tick_params(colors=tc, labelsize=13)
    ax.grid(color=np.array(C["border"]) / 255, alpha=0.45, lw=0.8)
    ax.set_xlim(-1.02, 1.02)
    ax.set_ylim(-1.15, 1.15)
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=5, frameon=False, fontsize=17,
                    labelcolor=np.array(C["text"]) / 255, handlelength=1.6)
    for h in leg.legend_handles:
        h.set_linewidth(4)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.09)
    return fig_to_img(fig)


def topology():
    cv = Canvas(1000, 560)
    cols = [(110, 7, "blue", "46 inputs"), (390, 8, "teal", "64 hidden"), (670, 8, "teal", "64 hidden"),
            (900, 4, "amber", "4 classes")]
    pos = []
    for x, n, col, lab in cols:
        span = 46 * (n - 1)
        ys = [290 - span / 2 + i * 46 for i in range(n)]
        pos.append((x, ys, col))
    for (x0, ys0, _), (x1, ys1, _) in zip(pos, pos[1:]):
        for a in ys0:
            for b in ys1:
                cv.line([x0, a, x1, b], (90, 120, 170, 70), 1.6)
    # highlight one learnable edge
    hx0, hy0 = pos[0][0], pos[0][1][2]
    hx1, hy1 = pos[1][0], pos[1][1][5]
    cv.line([hx0, hy0, hx1, hy1], "amber", 4)
    cv.text((hx0 + hx1) / 2 - 10, (hy0 + hy1) / 2 - 36, "φ(x)", 26, "bold", "amber", anchor="mm")
    for (x, ys, col), (_, n, _, lab) in zip(pos, cols):
        for y in ys:
            cv.circle(x, y, 13, fill="panel2", outline=col, width=3)
        if n > 4:
            cv.text(x, ys[-1] + 34, "⋮", 30, "symbol", "muted", anchor="mm")
        cv.text(x, 520, lab, 24, "semibold", "text", anchor="mm")
    for (x0, _, _), (x1, _, _), lab in zip(pos, pos[1:], ["2,944 edges", "4,096 edges", "256 edges"]):
        cv.text((x0 + x1) / 2, 40, lab, 21, "semibold", "muted", anchor="mm")
    return cv.img()


def param_table(w=720):
    rows = [("Layer", "Chebyshev", "Base", "Bias+LN", "Total"),
            ("46 → 64", "14,720", "2,944", "192", "17,856"),
            ("64 → 64", "20,480", "4,096", "192", "24,768"),
            ("64 → 4", "1,280", "256", "4", "1,540"),
            ("Total", "36,480", "7,296", "388", "44,164")]
    colx = [24, 300, 440, 570, w - 24]
    cv = Canvas(w, 360)
    cv.rrect(0, 0, w - 1, 359, r=18, fill="panel", outline="border", width=2)
    for r, row in enumerate(rows):
        y = 34 + r * 66
        if r == len(rows) - 1:
            cv.rrect(10, y - 26, w - 11, y + 30, r=10, fill=alpha("teal", 40))
        for i, cell in enumerate(row):
            kind = "semibold" if r in (0, len(rows) - 1) else "regular"
            col = "muted" if r == 0 else ("teal" if (r == len(rows) - 1 and i == 4) else "text")
            size = 30 if (r == len(rows) - 1 and i == 4) else 23
            anchor = "lm" if i == 0 else "rm"
            cv.text(colx[i], y + 2, cell, size, kind, col, anchor=anchor)
        if r == 0:
            cv.line([16, y + 28, w - 16, y + 28], "border", 2)
    return cv.img()


def b_math_kan(S):
    c = S.cue
    outA = c[4] - 0.3
    # MLP edge vs KAN edge
    e1 = panel(420, 260)
    e1.text(24, 18, "Ordinary network (MLP)", 25, "semibold", "muted")
    e1.circle(70, 140, 22, fill="panel2", outline="blue", width=3)
    e1.circle(350, 140, 22, fill="panel2", outline="teal", width=3)
    e1.line([92, 140, 328, 140], "muted", 4)
    e1.text(210, 110, "w", 30, "italic", "text", anchor="mm")
    e1.paste(M(r"y = w \cdot x", 36), 210, 190, anchor="ma")
    S.add(e1.img(), X0, 190, at=c[0], out=outA)

    e2 = panel(420, 260, border="amber")
    e2.text(24, 18, "ChebyKAN edge", 25, "semibold", "amber")
    e2.circle(70, 140, 22, fill="panel2", outline="blue", width=3)
    e2.circle(350, 140, 22, fill="panel2", outline="teal", width=3)
    pts = []
    for i in range(41):
        u = i / 40
        pts += [92 + 236 * u, 140 - 26 * math.sin(u * 2.4 * math.pi) * (1 - 0.3 * u)]
    e2.line(pts, "amber", 4)
    e2.paste(M(r"y = \phi(x)", 36), 210, 190, anchor="ma")
    S.add(e2.img(), X0 + 440, 190, at=c[1], out=outA)

    # Chebyshev recurrence + plot
    S.add(T("Chebyshev polynomials", 25, "semibold", "muted"), X0, 466, at=c[2], out=outA, anim="fade")
    S.add(M(r"T_0(x)=1,\qquad T_1(x)=x", 36), X0, 500, at=c[2], out=outA)
    S.add(M(r"T_{n+1}(x)=2x\,T_n(x)-T_{n-1}(x)", 36), X0, 550, at=c[2] + 1.2, out=outA)
    S.add(M(r"T_2=2x^2-1,\quad T_3=4x^3-3x,\quad T_4=8x^4-8x^2+1", 27, "muted"), X0, 604,
          at=c[2] + 2.4, out=outA)
    S.add(T("Basis on [−1, 1]", 22, "semibold", "muted"), 1000, 186, at=c[2] + 0.3, out=outA, anim="fade")
    S.add(cheb_plot(), 960, 210, at=c[2] + 0.3, out=outA, anim="fade")

    # edge equation
    eq = panel(CW, 222, fill="panel2", border="amber")
    eq.paste(M(r"\phi(x) \;=\; w_b\,x \;+\; \sum_{k=0}^{4} c_k\,T_k(\tanh x)", 60), 40, 111, anchor="lm")
    S.add(eq.img(), X0, 668, at=c[3], out=outA)
    chips = vstack([pill("1 base weight  w_b", "blue", 22), pill("5 Chebyshev coefficients  c₀…c₄", "teal", 22),
                    pill("= 6 learnable parameters per edge", "amber", 22, filled=True)], gap=12, halign="r")
    S.add(chips, X1 - 30, 686, at=c[3] + 2.0, out=outA, anim="right")

    # phase B: topology + parameter count
    S.add(topology(), X0, 200, at=c[4])
    S.add(T("Parameters", 25, "semibold", "muted"), 1120, 196, at=c[5], anim="fade")
    S.add(param_table(), 1120, 236, at=c[5])
    S.add(T("Design model: 4 classes → 44,164 parameters. The Car-Hacking experiment uses 5 classes "
            "→ 44,549.", 18, "regular", "dim", maxw=720), 1120, 610, at=c[5] + 1.0, anim="fade")
    bd = card(CW, 120, "Only additions and multiplications — no ReLU to approximate",
              "Polynomial activations map directly onto CKKS arithmetic, unlike ReLU or sigmoid.",
              accent="green", icon=icon_status("good", 34), title_size=27, body_size=22)
    S.add(bd, X0, 770, at=c[6])


# =================================================================== math: CKKS
def b_math_ckks(S):
    c = S.cue
    outA, outB = c[2] - 0.3, c[5] - 0.3
    S.add(M(r"R_q = \mathbb{Z}_q[X]\,/\,(X^N + 1),\qquad N = 8192\;\Rightarrow\;N/2 = 4096\ \mathrm{slots}", 42),
          X0, 196, at=c[0], out=outA)
    # one ciphertext, many slots
    n = 32
    sl = Canvas(CW, 120)
    sl.rrect(0, 20, CW - 1, 110, r=16, fill="panel2", outline="teal", width=3)
    cw = (CW - 40) / n
    for i in range(n):
        x = 20 + i * cw
        sl.rrect(x + 2, 34, x + cw - 2, 96, r=5, fill=alpha("teal", 60))
    for i, lab in [(0, "w₀"), (1, "w₁"), (2, "w₂"), (15, "…"), (16, "…"), (31, "w₄₀₉₅")]:
        sl.text(20 + i * cw + cw / 2, 65, lab, 20, "semibold", "text", anchor="mm")
    S.add(T("One ciphertext  ct = (c₀, c₁)  carries 4,096 weights. One addition updates all of them.",
            22, "regular", "muted"), X0, 282, at=c[0] + 1.2, out=outA, anim="fade")
    S.add(sl.img(), X0, 312, at=c[0] + 1.4, out=outA, anim="wipe", dur=1.0)

    S.add(M(r"m = \lfloor \Delta \cdot w \rceil,\qquad \Delta = 2^{40}\ \ (\approx 40\ \mathrm{bits\ of\ precision})", 38),
          X0, 470, at=c[1], out=outA)
    bw, gap = 150, (CW - 11 * 150) / 10
    for b in range(11):
        cv = Canvas(bw, 150)
        cv.rrect(0, 0, bw - 1, 149, r=12, fill="panel", outline="teal", width=2)
        if b < 10:
            cv.rrect(6, 40, bw - 7, 143, r=8, fill=alpha("teal", 110))
            cv.text(bw / 2, 92, "4,096", 24, "semibold", "text", anchor="mm")
        else:
            fill_w = (bw - 13) * 3204 / 4096
            cv.rrect(6, 40, 6 + fill_w, 143, r=8, fill=alpha("teal", 110))
            for k in range(0, 60, 9):
                xx = 6 + fill_w + k
                if xx < bw - 8:
                    cv.line([xx, 143, min(xx + 20, bw - 8), 40], "dim", 2)
            cv.text(bw / 2, 78, "3,204", 22, "semibold", "text", anchor="mm")
            cv.text(bw / 2, 108, "+ 892 pad", 17, "regular", "muted", anchor="mm")
        cv.text(bw / 2, 20, f"ct {b}", 18, "semibold", "muted", anchor="mm")
        S.add(cv.img(), X0 + b * (bw + gap), 570, at=c[1] + 1.4 + 0.12 * b, out=outA, anim="up", dur=0.4)
    S.add(T("44,164 weights  →  11 ciphertexts  ≈  3.5 MB per vehicle update", 26, "semibold", "teal"),
          W / 2, 750, at=c[1] + 3.0, out=outA, anchor="ma", anim="fade")

    # phase B: function F, depth 0, proof
    lines = [
        (r"\tilde{c}_k \;=\; n_k \odot c_k", "scale each encrypted update by its public sample count"),
        (r"c_{\mathrm{sum}} \;=\; \Sigma_{k=1}^{K}\; \tilde{c}_k", "add the ciphertexts slot by slot"),
        (r"c_F \;=\; \frac{1}{N} \odot c_{\mathrm{sum}},\qquad N = \Sigma_k\, n_k",
         "multiply by the plaintext scalar 1/N, no ciphertext division"),
    ]
    ys = [204, 292, 380]
    for i, ((tex, note), y) in enumerate(zip(lines, ys)):
        S.add(M(tex, 46), X0, y, at=c[2] + 1.4 * i, out=outB, anim="left")
        S.add(T(note, 23, "regular", "muted"), 900, y + 18, at=c[2] + 1.4 * i + 0.3, out=outB, anim="fade")
    S.add(pill("plaintext × ciphertext only  →  multiplicative depth 0", "green", 24), X0, 500, at=c[3],
          out=outB)
    pr = panel(CW, 214, fill="panel2", border="teal")
    pr.text(32, 24, "Correctness: decryption is linear", 25, "semibold", "teal")
    pr.paste(M(r"\mathrm{Dec}(c_F) \;=\; \Sigma_k\, \frac{n_k}{N}\,\mathrm{Dec}(c_k) \;=\; "
               r"\frac{\Sigma_k\, n_k\,\Delta w_k}{\Sigma_k\, n_k} \;=\; \Delta w_{\mathrm{global}}", 46), 32, 74)
    pr.text(32, 168, "Measured relative error 8.2 × 10⁻⁷, so accuracy matches plaintext FedAvg.", 22,
            "regular", "muted")
    S.add(pr.img(), X0, 600, at=c[4], out=outB)

    # phase C: robustness + noise refresh
    S.add(T("Encrypted robustness (FheFL distance)", 26, "semibold", "green"), X0, 196, at=c[5], anim="fade")
    S.add(M(r"d_k \;=\; \Vert w_k - g\Vert^2 \;=\; \Vert g\Vert^2 + \langle\, w_k - 2g,\; w_k \rangle", 42),
          X0, 244, at=c[5] + 0.3)
    S.add(T("one ciphertext × ciphertext multiply (depth 1)", 22, "regular", "muted"), X0, 320,
          at=c[5] + 1.2, anim="fade")
    S.add(M(r"p_k \;=\; 1 - \frac{d_k}{\Sigma_j\, d_j}", 46), X0, 380, at=c[5] + 2.4)
    S.add(T("trust weight: the server sees one number per vehicle, not 44,164 weights", 22, "regular",
            "muted", maxw=900), X0, 476, at=c[5] + 3.0, anim="fade")
    cost = panel(900, 250)
    cost.paste(T("Measured CKKS cost  ·  practical profile, N = 8192, 128-bit security", 22, "semibold",
                 "muted"), 24, 18)
    for i, (val, lab) in enumerate([("42 ms", "encrypt"), ("229 ms", "distance"), ("52 ms", "aggregate"),
                                    ("3.5 MB", "ciphertext")]):
        x = 24 + i * 216
        cost.paste(T(val, 40, "bold"), x, 70)
        cost.paste(T(lab, 21, "regular", "muted"), x, 130)
    cost.paste(T("max decryption error 3.2 × 10⁻⁸  ·  packing trims bandwidth by 29.6 %", 20, "regular",
                 "dim"), 24, 196)
    S.add(cost.img(), X0, 560, at=c[5] + 4.2)

    lp = Canvas(780, 560)
    boxes = [(40, 60, "Encrypt fresh", "scale 2⁴⁰, new noise", "amber"),
             (440, 60, "Aggregate F", "on ciphertexts", "violet"),
             (440, 340, "Decrypt", "the aggregate only", "teal"),
             (40, 340, "Local training", "next round", "blue")]
    for x, y, a, b, col in boxes:
        lp.rrect(x, y, x + 300, y + 130, r=16, fill="panel2", outline=col, width=3)
        lp.text(x + 150, y + 48, a, 26, "semibold", "text", anchor="mm")
        lp.text(x + 150, y + 90, b, 20, "regular", "muted", anchor="mm")
    lp.arrow(345, 125, 435, 125, color="muted", width=4)
    lp.arrow(590, 195, 590, 335, color="muted", width=4)
    lp.arrow(435, 405, 345, 405, color="muted", width=4)
    lp.arrow(190, 335, 190, 195, color="muted", width=4)
    lp.text(390, 265, "noise resets every round", 21, "semibold", "green", anchor="mm")
    lp.text(390, 520, "no bootstrapping needed", 22, "semibold", "green", anchor="mm")
    S.add(lp.img(), 1060, 230, at=c[6])


# =================================================================== results
def stat_compare(w, h, title, enc, plain, foot):
    cv = panel(w, h)
    cv.paste(T(title, 26, "semibold", maxw=w - 48), 24, 18)
    for i, (lab, val, col) in enumerate([("CKKS encrypted", enc, "teal"), ("Plaintext", plain, "dim")]):
        y = 84 + i * 72
        cv.rrect(24, y + 14, 42, y + 32, r=4, fill=col)
        cv.text(56, y + 23, lab, 22, "regular", "muted", anchor="lm")
        cv.text(w - 24, y + 23, val, 46, "bold", "text", anchor="rm")
    cv.paste(T(foot, 19, "regular", "muted", maxw=w - 48), 24, h - 46)
    return cv.img()


def stat_big(w, h, title, big, sub, color="text"):
    cv = panel(w, h)
    cv.paste(T(title, 26, "semibold", maxw=w - 48), 24, 18)
    cv.paste(T(big, 64, "bold", color), 24, 70)
    cv.paste(T(sub, 21, "regular", "muted", maxw=w - 48), 24, 168)
    return cv.img()


def b_results(S):
    c = S.cue
    S.add(T("Encryption costs no accuracy", 54, "bold"), X0, 184, at=c[0])
    S.add(T("3 seeds · 10 vehicles · 5 federated rounds · non-IID split (Dirichlet α = 0.3)", 23, "regular",
            "muted"), X0, 258, at=c[0] + 0.8, anim="fade")
    tw, th, g = (CW - 48) // 3, 268, 24
    xs = [X0 + i * (tw + g) for i in range(3)]
    y1, y2 = 310, 310 + th + g
    S.add(stat_compare(tw, th, "Car-Hacking  (main CAN benchmark)", "99.77 %", "99.81 %",
                       "gap −0.04 pp, inside the ±0.12 pp seed spread"), xs[0], y1, at=c[1])
    S.add(stat_compare(tw, th, "CICIDS-2017", "95.55 %", "95.42 %",
                       "gap +0.13 pp, inside the ±0.98 pp seed spread"), xs[1], y1, at=c[2])
    S.add(stat_big(tw, th, "Numerical error", "8.2 × 10⁻⁷",
                   "relative error of the encrypted aggregate vs plaintext"), xs[2], y1, at=c[3])
    S.add(stat_big(tw, th, "Privacy audit", "0", "individual updates decrypted, across every run"),
          xs[0], y2, at=c[3] + 1.2)
    S.add(stat_big(tw, th, "Cost: bandwidth", "3.5 MB",
                   "per encrypted update, about 21× the plaintext size"), xs[1], y2, at=c[4])
    lim = panel(tw, th)
    lim.paste(T("Honest limits", 26, "semibold"), 24, 18)
    lim.paste(status_row("warn", "CAN-VTC: 100 %", "flood detection, too easy to be meaningful", w=tw - 48,
                         label_size=22, detail_size=19), 24, 74)
    lim.paste(status_row("warn", "VeReMi: ≈ 48 %", "near chance until re-acquired with sender IDs",
                         w=tw - 48, label_size=22, detail_size=19), 24, 160)
    S.add(lim.img(), xs[2], y2, at=c[5])


# =================================================================== status
def b_status(S):
    c = S.cue
    # timeline
    tl = Canvas(CW, 170)
    ms = [("Months 1–4", "datasets, ChebyKAN, FHE study", "good"),
          ("Month 5", "audit + real CKKS pipeline", "good"),
          ("Aug – Oct", "function F, proof, multi-key study", "good"),
          ("Next", "OpenFHE multi-key", "todo"),
          ("Then", "embedded hardware", "todo"),
          ("Finally", "V2X, robustness, DP, paper", "todo")]
    m0 = 170
    step = (CW - 2 * m0) / (len(ms) - 1)
    tl.line([m0, 60, CW - m0, 60], "border", 4)
    tl.line([m0, 60, m0 + step * 2.5, 60], "green", 4)
    for i, (a, b, k) in enumerate(ms):
        x = m0 + i * step
        tl.paste(icon_status(k, 34), x - 17, 43)
        tl.text(x, 106, a, 21, "semibold", "text", anchor="mm")
        tl.text(x, 136, b, 18, "regular", "muted", anchor="mm")
    S.add(tl.img(), X0, 196, at=c[0] - 0.3, anim="wipe", dur=1.2)
    here = pill("we are here · Oct 2026", "amber", 19, filled=True)
    S.add(here, X0 + m0 + step * 2.5, 200, at=c[0] + 0.9, anchor="mb", anim="down")

    cy, chh = 386, 420
    done = panel(560, chh)
    done.paste(T("Done", 28, "semibold", "green"), 24, 18)
    items = ["Real CKKS federated pipeline", "Function F + correctness proof", "Encrypted robust weighting",
             "Packing: −29.6 % bandwidth", "NTT reference: 11.2× faster", "Conference paper draft"]
    for i, it in enumerate(items):
        done.paste(status_row("good", it, None, w=510, label_size=22), 24, 72 + i * 56)
    S.add(done.img(), X0, cy, at=c[0] + 0.4)

    mk = panel(600, chh, border="amber")
    mk.paste(T("Next: multi-key CKKS", 28, "semibold", "amber"), 24, 18)
    S.add(mk.img(), 660, cy, at=c[1])
    today = Canvas(552, 120)
    today.text(0, 4, "Today: one shared key", 22, "semibold", "text")
    for i in range(3):
        today.paste(icon_car(90, "blue"), i * 120, 40)
        today.paste(icon_key(30, "amber"), i * 120 + 84, 52)
    today.paste(T("TenSEAL has no multi-key API", 18, "regular", "muted", maxw=170), 372, 52)
    S.add(today.img(), 684, cy + 66, at=c[1] + 0.3, anim="fade")
    tgt = Canvas(552, 220)
    tgt.text(0, 4, "Target: every vehicle holds its own key share", 22, "semibold", "text")
    cols = ["teal", "violet", "green"]
    for i in range(3):
        tgt.paste(icon_car(90, "blue"), i * 120, 40)
        tgt.paste(icon_key(30, cols[i]), i * 120 + 84, 52)
    tgt.paste(M(r"\tilde{P} = \Sigma_i\, P_i", 34), 372, 44)
    tgt.paste(T("No single party can decrypt an individual update.", 19, "regular", "muted", maxw=540), 0, 104)
    tgt.paste(hstack([pill("CMK vs DMK-CKKS compared", "amber", 17, padx=12, pady=6),
                      pill("TenSEAL → OpenFHE", "teal", 17, padx=12, pady=6)], gap=10), 0, 150)
    S.add(tgt.img(), 684, cy + 196, at=c[2], anim="fade")

    hw = panel(560, chh, border="teal")
    hw.paste(icon_chip(54, "teal"), 24, 14)
    hw.paste(T("Then: hardware", 28, "semibold", "teal"), 92, 22)
    hitems = ["NXP S32G automotive board", "Raspberry Pi 5 (interim ARM host)", "ARM NEON NTT kernel",
              "INT8 quantisation", "On-vehicle IDS executable"]
    for i, it in enumerate(hitems):
        hw.paste(status_row("todo", it, None, w=510, label_size=22), 24, 86 + i * 62)
    S.add(hw.img(), 1280, cy, at=c[3])

    chips = [pill(t, "violet", 20, padx=14, pady=7) for t in
             ["V2X bandwidth: 3.5 MB update vs 2.7 KB frame", "Low-magnitude poisoning test",
              "Client-level differential privacy", "Re-acquire VeReMi"]]
    row = hstack(chips, gap=14)
    if row.width > CW:
        row = row.resize((CW, int(row.height * CW / row.width)), Image.LANCZOS)
    S.add(row, W / 2, cy + chh + 22, at=c[4], anchor="ma")


# =================================================================== summary
def b_summary(S):
    c = S.cue
    cw, g = 560, 40
    x0 = (W - 3 * cw - 2 * g) / 2
    cars = hstack([icon_car(110, "blue"), icon_car(110, "blue"), icon_car(110, "blue")], gap=8)
    srv = hstack([icon_server(70, 92, "violet"), icon_lock(60, "amber")], gap=14)
    pillars = [(cars, "Vehicles learn together", "One shared IDS; raw CAN data never leaves the car."),
               (srv, "The server computes blind", "Aggregation and robust weighting run on ciphertexts."),
               (icon_shield(90, "green"), "Privacy costs no accuracy", "99.77 % encrypted vs 99.81 % plaintext.")]
    for i, (ic, t, b) in enumerate(pillars):
        cv = panel(cw, 360)
        cv.paste(ic, cw / 2, 40, anchor="ma")
        cv.paste(T(t, 32, "semibold"), cw / 2, 170, anchor="ma")
        cv.paste(T(b, 23, "regular", "muted", maxw=cw - 60, align="center"), cw / 2, 228, anchor="ma")
        S.add(cv.img(), x0 + i * (cw + g), 230, at=c[0] + 0.5 * i)
    S.add(T("Thank you", 70, "bold"), W / 2, 650, at=c[1], anchor="ma")
    S.add(T("LG Soft India  ·  Privacy-Preserving Collaborative IDS for the Internet of Vehicles", 24,
            "regular", "muted"), W / 2, 756, at=c[1] + 0.5, anchor="ma", anim="fade")


BUILDERS = dict(title=b_title, problem=b_problem, approach=b_approach, data=b_data, attacks=b_attacks,
                math_kan=b_math_kan, math_ckks=b_math_ckks, results=b_results, status=b_status,
                summary=b_summary)

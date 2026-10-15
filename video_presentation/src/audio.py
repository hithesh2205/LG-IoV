"""Synthesised soundtrack: a soft background loop, small sound effects, and the final mix.

Everything is generated with numpy (no audio files, no downloads), so the build
stays self-contained. The music is ducked under the narration.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
MUSIC_GAIN = 0.63    # ~ -4 dB; keeps the music well under the voice


def _note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _pluck(freq, dur, decay):
    t = np.arange(int(dur * SR)) / SR
    tone = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t) + 0.08 * np.sin(6 * np.pi * freq * t)
    return tone * np.exp(-t / decay) * _env(len(t), 0.004, 0.02)


def music(total):
    """Gentle I–V–vi–IV loop (C, G, Am, F): pad + bass + arpeggio."""
    n = int(total * SR) + SR
    out = np.zeros(n)
    chords = [(48, [60, 64, 67]), (43, [59, 62, 67]), (45, [60, 64, 69]), (41, [60, 65, 69])]
    bar = 4 * BEAT
    chord_len = 2 * bar
    t_all = np.arange(int(chord_len * SR + 0.8 * SR)) / SR
    k = 0
    t0 = 0.0
    while t0 < total + 1:
        root, tones = chords[k % 4]
        i0 = int(t0 * SR)
        # pad
        pad = np.zeros_like(t_all)
        for m in tones:
            f = _note(m)
            pad += np.sin(2 * np.pi * f * t_all) * (1 + 0.15 * np.sin(2 * np.pi * 0.3 * t_all))
            pad += 0.3 * np.sin(2 * np.pi * 2 * f * t_all + 0.5)
        pad *= _env(len(t_all), 0.8, 0.8) * 0.035
        seg = out[i0:i0 + len(pad)]
        seg += pad[:len(seg)]
        # bass on beats 1 and 3
        for b in (0, 2, 4, 6):
            j = i0 + int(b * BEAT * SR)
            s = _pluck(_note(root - 12), 1.2, 0.45) * 0.10
            seg2 = out[j:j + len(s)]
            seg2 += s[:len(seg2)]
        # arpeggio on eighth notes
        arp = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 12]
        for e in range(16):
            j = i0 + int(e * BEAT / 2 * SR)
            s = _pluck(_note(arp[e % 4]), 0.6, 0.18) * (0.045 if e % 2 == 0 else 0.03)
            seg3 = out[j:j + len(s)]
            seg3 += s[:len(seg3)]
        t0 += chord_len
        k += 1
    out = out[: int(total * SR)]
    fade = int(2.5 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def sfx(kind):
    if kind == "pop":
        t = np.arange(int(0.12 * SR)) / SR
        f = 700 + 900 * t / t[-1]
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * 0.22
    if kind == "whoosh":
        n = int(0.7 * SR)
        rng = np.random.default_rng(1)
        noise = rng.standard_normal(n)
        y = np.zeros(n)
        a = 0.0
        for i in range(n):          # one-pole low-pass with a rising then falling cutoff
            c = 0.02 + 0.25 * np.sin(np.pi * i / n) ** 2
            a += c * (noise[i] - a)
            y[i] = a
        return y * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.30
    if kind == "ding":
        t = np.arange(int(0.9 * SR)) / SR
        return (np.sin(2 * np.pi * 1046.5 * t) + 0.6 * np.sin(2 * np.pi * 1568 * t)) * np.exp(-t / 0.25) * 0.12
    if kind == "alert":
        t = np.arange(int(0.42 * SR)) / SR
        gate = ((t % 0.21) < 0.13).astype(float)
        tone = np.sign(np.sin(2 * np.pi * 330 * t)) * 0.5 + np.sin(2 * np.pi * 330 * t) * 0.5
        return tone * gate * np.exp(-t / 0.3) * 0.07
    if kind == "click":
        t = np.arange(int(0.06 * SR)) / SR
        return np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.008) * 0.25
    if kind == "rise":
        t = np.arange(int(1.0 * SR)) / SR
        f = 300 + 500 * t
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / t[-1]) ** 2 * np.exp(-(t - 1) ** 2 / 0.02) * 0.10
    raise ValueError(kind)


def _read_wav(path):
    with wave.open(str(path)) as w:
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    if rate != SR:
        x = np.arange(len(pcm)) / rate
        pcm = np.interp(np.arange(int(len(pcm) * SR / rate)) / SR, x, pcm)
    return pcm


def mix(total, voice_events, sfx_events, out_path: Path, with_music=True):
    """voice_events: [(start_s, wav_path)], sfx_events: [(start_s, kind)]."""
    n = int(total * SR)
    voice = np.zeros(n)
    for t, p in voice_events:
        pcm = _read_wav(p)
        i = int(t * SR)
        seg = voice[i:i + len(pcm)]
        seg += pcm[:len(seg)]
    peak = np.max(np.abs(voice)) or 1
    voice *= 0.89 / peak

    fx = np.zeros(n)
    cache = {}
    for t, kind in sfx_events:
        s = cache.get(kind)
        if s is None:
            s = cache[kind] = sfx(kind)
        i = max(0, int(t * SR))
        seg = fx[i:i + len(s)]
        seg += s[:len(seg)]

    out = voice + fx
    if with_music:
        m = music(total)[:n]
        # duck the music under speech (smoothed speech envelope)
        env = np.abs(voice)
        win = int(0.25 * SR)
        cs = np.concatenate([[0.0], np.cumsum(env)])          # O(n) moving average
        half = win // 2
        idx = np.arange(n)
        lo, hi = np.clip(idx - half, 0, n), np.clip(idx + half, 0, n)
        env = (cs[hi] - cs[lo]) / win
        env = np.clip(env / (np.percentile(env[env > 0], 90) if np.any(env > 0) else 1), 0, 1)
        out += MUSIC_GAIN * m * (1 - 0.45 * env)
    out = np.clip(out, -1, 1)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())

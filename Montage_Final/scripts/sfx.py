"""Sound design synthétique (numpy) : whoosh, impact, pop. Aucun fichier externe, libre de droits."""
import wave

import numpy as np

SR = 48000
_rng = np.random.default_rng(7)


def whoosh(dur=0.7, up=True):
    n = int(SR * dur)
    x = _rng.standard_normal(n)
    sweep = np.linspace(0.015, 0.35, n) if up else np.linspace(0.35, 0.015, n)
    y, lp = np.zeros(n), 0.0
    for i in range(n):  # passe-bas à fréquence glissante
        lp += sweep[i] * (x[i] - lp)
        y[i] = lp
    y -= np.convolve(y, np.ones(400) / 400, mode="same")  # retire les graves
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    y *= env
    return 0.9 * y / (np.abs(y).max() + 1e-9)


def impact(dur=0.9):
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (55 + 40 * np.exp(-t * 18)) * t) * np.exp(-t * 5)
    noise = np.convolve(_rng.standard_normal(n), np.ones(30) / 30, mode="same") * np.exp(-t * 14)
    y = body + 0.5 * noise
    return 0.95 * y / (np.abs(y).max() + 1e-9)


def pop(dur=0.14):
    n = int(SR * dur)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (900 - 3500 * t) * t) * np.exp(-t * 28)
    return 0.8 * y


KINDS = {"whoosh": lambda: whoosh(0.7), "whoosh_down": lambda: whoosh(0.8, False),
         "impact": impact, "pop": pop}


def render(events, total, path):
    """events : [(t_sec, kind, gain)] -> WAV stéréo 48 kHz de durée 'total'."""
    buf = np.zeros(int(SR * total) + SR)
    for t, kind, gain in events:
        s = KINDS[kind]()
        i = int(max(0, t) * SR)
        buf[i:i + len(s)] += s[:len(buf) - i] * gain
    buf = np.clip(buf, -1, 1)
    pcm = (np.repeat(buf[:, None], 2, axis=1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

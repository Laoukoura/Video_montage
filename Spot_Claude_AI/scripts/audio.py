#!/usr/bin/env python3
"""Bande-son du spot : musique originale synthétisée + bruitages + voix off mixée.

Musique « corporate inspirante » 100 BPM, grille Am–F–C–G, construite en sections
calées sur les plans (intro feutrée, montée, pause sur « 100 % », final sur l'appel
à l'inscription). Aucun échantillon externe : tout est généré ici (libre de droits).
Sortie : build/mix.wav (48 kHz stéréo, voix + musique + SFX, avant normalisation).
"""
import subprocess
import wave

import numpy as np

import plan

SR = 48000
BPM = 100.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)

# Grille : Am  F  C  G  (fondamentales MIDI) + voicings
PROG = [
    (45, [57, 60, 64, 69]),   # Am
    (41, [57, 60, 65, 69]),   # F
    (48, [55, 60, 64, 67]),   # C
    (43, [55, 59, 62, 67]),   # G
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sr=SR):
    e = np.ones(n)
    na, nr = max(1, int(a * sr)), max(1, int(r * sr))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cutoff):
    """Passe-bas spectral (FFT) – suffisant pour du design sonore hors temps réel."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X * (g[:, None] if x.ndim == 2 else g), n=len(x), axis=0)


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def reverb(x, secs=2.2, mix=0.25):
    n = int(secs * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / secs)
        ir = lowpass(ir, 5000)
        ir /= np.sqrt((ir ** 2).sum())
        L = len(x) + n
        nfft = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[:, c], nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
        out[:, c] = y
    return x * (1 - mix) + out * mix * 1.6


def add(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l, sig * r], 1) * 1.414
    j = min(len(buf), i + len(sig))
    if i < 0:
        sig, i = sig[-i:], 0
    buf[i:j] += sig[: j - i] * gain


# --------------------------------------------------------------------------- instruments
def pad_chord(notes, dur, bright):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for m in notes:
        for k, det in enumerate((-0.09, 0.0, 0.11)):
            f0 = hz(m + det)
            sig = np.zeros(n)
            for h in range(1, 14):
                if f0 * h > 9000:
                    break
                sig += np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 6.28)) / h * np.exp(-h / bright)
            pan = (-0.6, 0.0, 0.6)[k]
            out[:, 0] += sig * np.cos((pan + 1) * np.pi / 4)
            out[:, 1] += sig * np.sin((pan + 1) * np.pi / 4)
    return out * env_adsr(n, 0.35, 0.5)[:, None] * 0.05


def pluck(m, dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    sig = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t * 18)
           + 0.15 * np.sin(6 * np.pi * f * t) * np.exp(-t * 30))
    return sig * np.exp(-t * 7) * env_adsr(n, 0.003, 0.05)


def piano(m, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    sig = sum(np.sin(2 * np.pi * f * h * t * (1 + 0.0004 * h * h)) * np.exp(-t * (2 + h * 1.4)) / h
              for h in range(1, 7))
    return sig * env_adsr(n, 0.004, 0.2)


def bass(m, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return np.tanh(sig * 1.6) * env_adsr(n, 0.01, 0.08) * np.exp(-t * 1.2)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.2 * np.sin(ph) * np.exp(-t * 7.5)) + 0.15 * rng.standard_normal(n) * np.exp(-t * 300)


def clap():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    nz = highpass(rng.standard_normal(n), 900)
    e = np.exp(-t * 22) + 0.6 * np.exp(-np.abs(t - 0.012) * 400) + 0.5 * np.exp(-np.abs(t - 0.024) * 400)
    return nz * e * 0.5


def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.35


def whoosh(dur=0.6, up=True):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    nz = rng.standard_normal(n)
    # balayage de filtre par tranches
    out = np.zeros(n)
    seg = 1024
    for i in range(0, n, seg):
        p = i / n if up else 1 - i / n
        fc = 300 + 7000 * p ** 2
        blk = nz[i:i + seg]
        out[i:i + seg] = lowpass(highpass(blk, fc * 0.4), fc)
    e = np.sin(np.pi * t) ** 1.5
    return out * e * 0.9


def impact():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    crack = lowpass(rng.standard_normal(n), 3500) * np.exp(-t * 14) * 0.5
    return np.tanh(1.6 * (boom + crack))


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    p = t / dur
    f = 180 * 2 ** (p * 3)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    nz = highpass(rng.standard_normal(n), 2500) * 0.6
    return (tone + nz * p) * p ** 2.2


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 25) + 300
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.8


def click():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 3000) * np.exp(-t * 300) * 0.6


def shimmer(dur=1.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * hz(m) * t + rng.uniform(0, 6)) * np.exp(-t * (2.2 + i * 0.4))
              for i, m in enumerate((81, 84, 88, 93, 96)))
    return sig * env_adsr(n, 0.01, 0.3) * 0.18


# --------------------------------------------------------------------------- musique
def music(total, P):
    n = int((total + 3) * SR)
    mus = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    sc = np.ones(n)                         # enveloppe de sidechain (pompe du kick)

    t_claude = P["lines"]["claude"]["speech"][0] - 0.2
    t_break = plan.word_time("mobile", "Cent") - 0.05
    t_break_end = plan.word_time("mobile", "téléphone") + 0.55
    t_cta = P["lines"]["cta"]["speech"][0] - 0.22
    t_end = P["lines"]["cta"]["end"] + 1.2

    nbars = int(np.ceil(total / BAR)) + 1
    t0 = 0.0
    for b in range(nbars):
        tb = t0 + b * BAR
        if tb > total + 0.5:
            break
        root, voicing = PROG[b % 4]
        bright = 2.0 + 6.0 * min(1, tb / 25)            # le filtre s'ouvre progressivement
        if tb >= t_cta - 0.1:
            bright = 9
        add(mus, pad_chord(voicing, BAR + 0.6, bright), tb, 1.0)
        in_break = t_break - BAR * 0.5 < tb < t_break_end
        for s in range(8):                                 # arpège en croches
            ts = tb + s * BEAT / 2
            if ts > t_end:
                break
            if t_break <= ts < t_break_end:
                continue
            note = voicing[[0, 1, 2, 3, 2, 1, 3, 2][s]] + 12
            g = 0.10 if tb < t_claude else 0.13
            add(mus, pluck(note), ts, g, pan=(-0.35 if s % 2 else 0.35))
            add(mus, pluck(note + 12, 0.3), ts + BEAT * 0.75, g * 0.25, pan=(0.6 if s % 2 else -0.6))
        if tb >= t_claude - 0.1 and not in_break:
            for q in range(4):                              # basse en noires
                tq = tb + q * BEAT
                if t_break <= tq < t_break_end or tq > t_end:
                    continue
                add(mus, bass(root, BEAT * 0.95), tq, 0.32)
        # piano mélodique sur les temps forts
        mel = [76, 72, 72, 74][b % 4] if b % 2 == 0 else [74, 72, 76, 71][b % 4]
        if tb >= t_claude and not (t_break <= tb < t_break_end) and tb < t_end:
            add(mus, piano(mel), tb, 0.09, pan=0.1)
            add(mus, piano(mel - 5, 1.2), tb + BEAT * 2.5, 0.06, pan=-0.1)

    # batterie : entre sur « Claude AI », coupure sur « 100 % », plein régime à la fin
    t = t_claude
    beat_i = 0
    while t < t_end:
        if not (t_break <= t < t_break_end):
            add(drums, kick(), t, 0.55)
            i0 = int(t * SR)
            k = np.arange(min(int(0.32 * SR), n - i0))
            sc[i0:i0 + len(k)] = np.minimum(sc[i0:i0 + len(k)], 0.55 + 0.45 * (k / len(k)) ** 0.6)
            if beat_i % 2 == 1:
                add(drums, clap(), t, 0.42)
            add(drums, hat(), t + BEAT / 2, 0.30, pan=0.3)
            if t >= t_cta - 0.1:
                add(drums, hat(), t + BEAT / 4, 0.14, pan=-0.3)
                add(drums, hat(), t + 3 * BEAT / 4, 0.14, pan=-0.3)
            if beat_i % 8 == 7:
                add(drums, hat(True), t + BEAT / 2, 0.2, pan=-0.2)
        t += BEAT
        beat_i += 1

    mus *= sc[:, None]
    mus = reverb(mus, 2.4, 0.3)
    drums = reverb(drums, 0.9, 0.12)
    out = mus + drums
    # fin : accord tenu + fondu
    fade_n = int(2.6 * SR)
    i_end = int(t_end * SR)
    out[i_end:i_end + fade_n] *= np.linspace(1, 0, min(fade_n, n - i_end))[:, None] ** 2
    out[i_end + fade_n:] = 0
    tail = reverb(pad_chord(PROG[0][1], 3.0, 6) + 0, 3.0, 0.5)
    add(out, tail, t_end - 0.1, 0.9)
    # fondu d'entrée
    k = int(0.6 * SR)
    out[:k] *= np.linspace(0, 1, k)[:, None]
    return out, (t_break, t_break_end, t_cta, t_end)


def sfx(n, P, marks):
    out = np.zeros((n, 2))
    t_break, t_break_end, t_cta, t_end = marks
    # transitions : whoosh centré sur chaque coupe
    for s in P["scenes"][1:]:
        add(out, whoosh(0.55, up=True), s["start"] - 0.32, 0.30, pan=rng.uniform(-0.4, 0.4))
    add(out, riser(1.0), P["scenes"][1]["start"] - 1.0, 0.25)
    add(out, impact(), P["scenes"][1]["start"] - 0.02, 0.55)
    # mots clés
    add(out, impact(), plan.word_time("claude", "Claude") - 0.02, 0.38)
    add(out, shimmer(), plan.word_time("claude", "Claude") + 0.02, 0.8)
    add(out, impact(), plan.word_time("mobile", "Cent") - 0.03, 0.6)
    add(out, shimmer(2.2), plan.word_time("mobile", "Cent"), 0.9)
    add(out, riser(1.2), t_cta - 1.2, 0.22)
    add(out, impact(), t_cta - 0.02, 0.5)
    add(out, shimmer(2.4), plan.word_time("cta", "Claude"), 0.8)
    # pops UI : puces de la scène « montage » et plateformes
    for w in ("Script", "découpage", "sous-titres", "musique", "effets"):
        add(out, pop(), plan.word_time("montage", w) - 0.02, 0.35, pan=rng.uniform(-0.5, 0.5))
    for w in ("TikTok", "Reels", "WhatsApp"):
        add(out, pop(), plan.word_time("publier", w) - 0.02, 0.35, pan=rng.uniform(-0.5, 0.5))
    for w in ("ordinateur", "compliqué"):
        add(out, whoosh(0.3, up=False), plan.word_time("mobile", w) + 0.15, 0.25)
    # frappe clavier / clics de l'assistant
    t = plan.word_time("claude", "intelligence")
    for i in range(16):
        add(out, click(), t + i * 0.11 + rng.uniform(0, 0.03), 0.18, pan=rng.uniform(-0.3, 0.3))
    add(out, click(), plan.word_time("cta", "Inscris") + 0.3, 0.5)
    add(out, pop(), plan.word_time("cta", "Inscris") + 0.32, 0.5)
    return reverb(out, 1.2, 0.15)


def voice(n, P):
    out = np.zeros((n, 2))
    env = np.zeros(n)
    for k in P["order"]:
        ln = P["lines"][k]
        wav = plan.BUILD / ("vo_fx_" + ln["wav"])
        # traitement voix : passe-haut, présence, compression douce, rééchantillonnage 48 kHz
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(plan.BUILD / ln["wav"]), "-af",
                        "highpass=f=75,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=3.5,"
                        "equalizer=f=7500:t=q:w=1:g=1.5,acompressor=threshold=-20dB:ratio=3:attack=4:"
                        "release=90:makeup=2,aresample=48000", "-ac", "1", str(wav)], check=True)
        x, sr = plan.read_wav(wav)
        add(out, x, ln["start"], 1.0)
        i = int(ln["start"] * SR)
        j = min(n, i + len(x))
        env[i:j] = np.maximum(env[i:j], 1.0)
    # enveloppe de ducking lissée (attaque 80 ms, relâche 350 ms)
    k = int(0.35 * SR)
    sm = np.convolve(env, np.ones(k) / k, "same")
    return out, np.clip(sm * 1.3, 0, 1)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    P = plan.load()
    total = P["total"]
    mus, marks = music(total, P)
    n = int(total * SR)
    mus = mus[:n]
    fx = sfx(n, P, marks)
    vo, duck = voice(n, P)
    mus_gain = (0.62 - 0.40 * duck)[:, None]          # ~ -8 dB sous la voix
    mix = mus * mus_gain + fx * 0.85 + vo * 1.0
    # fondu final
    k = int(0.5 * SR)
    mix[-k:] *= np.linspace(1, 0, k)[:, None]
    peak = np.abs(mix).max()
    mix *= 0.89 / peak
    write_wav(plan.BUILD / "mix.wav", mix)
    write_wav(plan.BUILD / "musique_seule.wav", mus * 0.89 / max(1e-9, np.abs(mus).max()))
    print("mix.wav :", round(total, 2), "s, crête", round(float(peak), 3))


if __name__ == "__main__":
    main()

"""Plan de montage commun à l'audio et à la vidéo.

Calcule, à partir des répliques de voix off (build/vo.json) :
  * le placement de chaque réplique sur la timeline,
  * un horodatage approché mot par mot (ancré sur les pauses réelles de la voix),
  * les bornes de chaque plan et des transitions.
"""
import json
import re
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
IMAGES = ROOT / "images"

W, H, FPS = 1080, 1920, 30
INTRO = 1.05        # ouverture (logo + flash) avant la première réplique
GAP = 0.55          # respiration entre deux répliques
OUTRO_HOLD = 3.4    # tenue de l'écran d'inscription après la dernière réplique
TRANS = 0.42        # durée des transitions entre plans

# Transition utilisée pour ENTRER dans chaque plan
TRANSITIONS = {
    "hook": "flash", "claude": "whip", "montage": "zoom", "mobile": "whip_up",
    "publier": "leak", "afrique": "whip", "cta": "glitch",
}


def read_wav(path):
    with wave.open(str(path)) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x, sr


def _pauses(x, sr, min_gap=0.07):
    """Retourne les milieux des pauses internes (s) triées par longueur décroissante."""
    hop = int(sr * 0.01)
    env = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same")[::hop])
    thr = max(env.max() * 0.06, 1e-4)
    quiet = env < thr
    gaps, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if i > 0 and j < len(quiet) and (j - i) * 0.01 >= min_gap:
                gaps.append(((j - i) * 0.01, (i + j) / 2 * 0.01))
            i = j
        else:
            i += 1
    # début/fin réels de la parole
    voiced = np.where(~quiet)[0]
    s0, s1 = (voiced[0] * 0.01, voiced[-1] * 0.01) if len(voiced) else (0, len(x) / sr)
    return sorted(gaps, reverse=True), s0, s1


def _chunks(text):
    """Découpe une réplique en groupes de souffle (ponctuation)."""
    parts = re.split(r"(?<=[,.;:!?…])\s+", text.strip())
    return [p for p in parts if p]


def _align(chunks, gaps, s0, s1):
    """Frontières entre groupes de souffle : choix optimal (programmation dynamique)
    d'une pause réelle par frontière, en favorisant les pauses longues et proches de la
    position attendue au prorata du texte."""
    K = len(chunks) - 1
    if K == 0:
        return []
    tot = sum(len(c) for c in chunks)
    exp, acc = [], 0
    for c in chunks[:-1]:
        acc += len(c)
        exp.append(s0 + (s1 - s0) * acc / tot)
    cand = sorted((m, L) for L, m in gaps if s0 + 0.15 < m < s1 - 0.15)
    N = len(cand)
    if N < K:
        return exp
    INF = 1e9
    cost = [[INF] * N for _ in range(K)]
    back = [[-1] * N for _ in range(K)]
    for j, (m, L) in enumerate(cand):
        cost[0][j] = abs(m - exp[0]) - 10 * L
    for k in range(1, K):
        for j, (m, L) in enumerate(cand):
            c = abs(m - exp[k]) - 10 * L
            for i in range(j):
                if cost[k - 1][i] + c < cost[k][j]:
                    cost[k][j], back[k][j] = cost[k - 1][i] + c, i
    j = min(range(N), key=lambda j: cost[K - 1][j])
    out = []
    for k in range(K - 1, -1, -1):
        out.append(cand[j][0])
        j = back[k][j]
    return out[::-1]


@lru_cache(None)
def load():
    vo = json.loads((BUILD / "vo.json").read_text())
    t = INTRO
    lines = []
    for i, ln in enumerate(vo):
        x, sr = read_wav(BUILD / ln["wav"])
        gaps, s0, s1 = _pauses(x, sr)
        chunks = _chunks(ln["text"])
        bounds = _align(chunks, gaps, s0, s1)
        edges = [s0] + bounds + [s1]
        words = []
        for ci, c in enumerate(chunks):
            a, b = edges[ci], edges[ci + 1]
            if ci > 0:
                a += 0.04
            ws = []
            for w in c.split():   # « montage ? » -> un seul mot
                if ws and not re.search(r"\w", w):
                    ws[-1] += " " + w
                else:
                    ws.append(w)
            weights = [len(re.sub(r"\W", "", w)) + 2 for w in ws]
            tot, acc = sum(weights), 0
            for w, wt in zip(ws, weights):
                ws_t = a + (b - a) * acc / tot
                acc += wt
                words.append({"w": w, "t0": t + ws_t, "t1": t + a + (b - a) * acc / tot, "chunk": ci})
        # lissage : moyenne avec une répartition purement proportionnelle sur toute la
        # réplique (évite qu'une mauvaise pause écrase un groupe de mots)
        wts = [len(re.sub(r"\W", "", w["w"])) + 2 for w in words]
        tot, acc = sum(wts), 0
        for w, wt in zip(words, wts):
            p0 = t + s0 + (s1 - s0) * acc / tot
            acc += wt
            p1 = t + s0 + (s1 - s0) * acc / tot
            w["t0"], w["t1"] = 0.5 * (w["t0"] + p0), 0.5 * (w["t1"] + p1)
        lines.append({**ln, "start": t, "end": t + ln["dur"], "speech": (t + s0, t + s1),
                      "chunks": chunks, "words": words})
        t += ln["dur"] + GAP
    total = lines[-1]["end"] + OUTRO_HOLD
    # plans : un par réplique (+ intro). La coupe tombe juste avant le début de la parole.
    scenes = [{"key": "intro", "start": 0.0}]
    for ln in lines:
        scenes.append({"key": ln["key"], "start": ln["speech"][0] - 0.22})
    for a, b in zip(scenes, scenes[1:]):
        a["end"] = b["start"]
    scenes[-1]["end"] = total
    return {"lines": {ln["key"]: ln for ln in lines}, "order": [ln["key"] for ln in lines],
            "scenes": scenes, "total": total}


def word_time(key, needle, which="t0", occurrence=0):
    """Instant (absolu) où le mot contenant `needle` est prononcé dans la réplique `key`."""
    n = 0
    for w in load()["lines"][key]["words"]:
        if needle.lower() in w["w"].lower():
            if n == occurrence:
                return w[which]
            n += 1
    raise KeyError(f"{needle!r} absent de {key}")


if __name__ == "__main__":
    p = load()
    for s in p["scenes"]:
        print(f'{s["key"]:8s} {s["start"]:6.2f} -> {s["end"]:6.2f}')
    for k in p["order"]:
        ln = p["lines"][k]
        print(k, [f'{w["w"]}@{w["t0"]:.2f}' for w in ln["words"]])
    print("TOTAL", round(p["total"], 2))

"""Étape I/J : contrôle qualité (ffprobe, intégrité, loudness, noir final) + images + rapport."""
import re
from pathlib import Path

import common
from common import DIRS, log, probe, run

EXPECT = {"v": (1080, 1920), "h": (1920, 1080)}


def loudness(path):
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true",
             "-vn", "-f", "null", "-"], check=False)
    tail = p.stderr[p.stderr.rfind("Summary"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(i.group(1)) if i else None, float(pk.group(1)) if pk else None)


def check(fmt, path, expected_duration, plan_times):
    path = Path(path)
    res = {"fichier": str(path), "ok": True, "problemes": []}
    if not path.exists():
        res.update(ok=False, problemes=["fichier absent"])
        return res
    info = probe(path)
    v, a = info["video"], info["audio"]
    W, H = EXPECT[fmt]
    if not v or (v["w"], v["h"]) != (W, H):
        res["problemes"].append(f"résolution {v and (v['w'], v['h'])} != {(W, H)}")
    if not v or v["codec"] != "h264":
        res["problemes"].append("codec vidéo != h264")
    if not a or a["codec"] != "aac":
        res["problemes"].append("piste audio AAC absente")
    if abs(info["duration"] - expected_duration) > 0.25:
        res["problemes"].append(f"durée {info['duration']:.2f}s != attendue {expected_duration:.2f}s")
    dec = run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"], check=False)
    if dec.returncode != 0 or dec.stderr.strip():
        res["problemes"].append("erreurs de décodage : " + dec.stderr.strip()[:200])
    lufs, peak = loudness(path)
    if peak is not None and peak > -0.5:
        res["problemes"].append(f"crête audio {peak} dBFS (saturation possible)")
    bd = run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "blackdetect=d=0.5:pix_th=0.05",
              "-an", "-f", "null", "-"], check=False)
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd.stderr)
    if blacks:
        res["problemes"].append(f"séquences noires : {blacks}")
    res.update(info=info, lufs=lufs, peak=peak, ok=not res["problemes"])
    # images : intro, accroche/titre, milieu, mot-clé, conclusion
    out = DIRS["rapport"] / f"images_{fmt}"
    out.mkdir(exist_ok=True)
    d = info["duration"]
    times = sorted({0.4, plan_times.get("title", 1.0) + 0.9, d * 0.5, plan_times.get("callout", d * 0.3) + 0.8,
                    d - 2.0, d - 0.3})
    frames = []
    for k, t in enumerate(times):
        t = max(0, min(t, d - 0.05))
        f = out / f"f{k}_{t:.1f}s.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
             "-vf", "scale=-2:720", f])
        frames.append(f)
    res["images"] = [str(f) for f in frames]
    return res


def write_report(results, notes, path=None):
    path = Path(path or DIRS["rapport"] / "rapport_montage.txt")
    L = ["RAPPORT DE MONTAGE", "=" * 60, ""]
    for fmt, r in results.items():
        L.append(f"[{fmt.upper()}] {r['fichier']}")
        if "info" in r:
            v, a = r["info"]["video"], r["info"]["audio"]
            L.append(f"  {v['w']}x{v['h']} {v['codec']} {v['fps']} fps | {a['codec']} {a['rate']} Hz | "
                     f"{r['info']['duration']:.2f}s | {r['lufs']} LUFS | crête {r['peak']} dBFS")
        L.append("  Contrôle : " + ("OK" if r["ok"] else "PROBLÈMES -> " + "; ".join(r["problemes"])))
        L += ["  Images extraites : " + ", ".join(r.get("images", [])), ""]
    L += ["NOTES / LIMITES", "-" * 60] + [f"- {n}" for n in notes]
    path.write_text("\n".join(L), encoding="utf-8")
    log.info("Rapport : %s", path)
    return path

"""Étape A : inventaire des rushes, métadonnées, silences, luminosité, visage.

Usage : python analyse.py DOSSIER_OU_FICHIERS... -> intermediaires/analyse.json
"""
import argparse
import re
import statistics
import sys
from pathlib import Path

import common
from common import DIRS, log, probe, run

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf"}


def find_rushes(inputs):
    files = []
    for i in inputs:
        p = Path(i)
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT)
        elif p.is_file():
            files.append(p)
        else:
            raise common.MontageError(f"Introuvable : {p}")
    if not files:
        raise common.MontageError("Aucun fichier vidéo trouvé.")
    return files


def silences(path, noise=-32, d=0.4):
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn",
             "-af", f"silencedetect=noise={noise}dB:d={d}", "-f", "null", "-"], check=False)
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    return list(zip(s, e))


def luma(path, duration):
    """Luminance moyenne (YAVG) échantillonnée toutes les ~4 s."""
    step = max(4.0, duration / 40)
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an",
             "-vf", f"fps=1/{step:.2f},signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
             "-f", "null", "-"], check=False)
    vals = [float(x) for x in re.findall(r"YAVG=([\d.]+)", p.stdout)]
    return round(statistics.median(vals), 1) if vals else None


def face_x(path, duration, out_dir):
    """Position horizontale médiane du visage (0-1) si OpenCV est disponible."""
    try:
        import cv2
    except ImportError:
        log.info("  OpenCV absent : pas de détection de visage (cadrage centré ou --focus-x)")
        return None
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs = []
    for k in range(1, 9):
        t = duration * k / 9
        jpg = out_dir / f"{Path(path).stem}_{k}.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", path,
             "-frames:v", "1", "-vf", "scale=640:-2", jpg])
        img = cv2.imread(str(jpg), cv2.IMREAD_GRAYSCALE)
        faces = cas.detectMultiScale(img, 1.1, 5, minSize=(40, 40))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + w / 2) / img.shape[1])
    return round(statistics.median(xs), 3) if xs else None


def analyse(files):
    DIRS["inter"].mkdir(parents=True, exist_ok=True)
    frames = DIRS["inter"] / "frames"
    frames.mkdir(exist_ok=True)
    out = []
    for f in files:
        log.info("Analyse : %s", f.name)
        info = probe(f)
        if not info["video"] or not info["audio"]:
            raise common.MontageError(f"{f.name} : il faut une piste vidéo ET audio.")
        info["silences"] = silences(f)
        info["luma"] = luma(f, info["duration"])
        info["face_x"] = face_x(f, info["duration"], frames)
        # images d'échantillon (début, milieu, fin) pour contrôle visuel
        for tag, frac in (("debut", 0.03), ("milieu", 0.5), ("fin", 0.95)):
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{info['duration'] * frac:.2f}", "-i", f,
                 "-frames:v", "1", "-vf", "scale=960:-2", frames / f"{f.stem}_{tag}.jpg"])
        log.info("  %dx%d @%.2f fps, %.1fs, luma=%s, %d silences, visage x=%s",
                 info["video"]["w"], info["video"]["h"], info["video"]["fps"],
                 info["duration"], info["luma"], len(info["silences"]), info["face_x"])
        out.append(info)
    need = sum(Path(f).stat().st_size for f in files) * 3
    log.info("Espace estimé pour intermédiaires + exports : ~%.1f Go", need / 1e9)
    common.save_json(DIRS["inter"] / "analyse.json", {"files": out})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args(argv)
    common.setup_logging()
    analyse(find_rushes(a.inputs))


if __name__ == "__main__":
    try:
        main()
    except common.MontageError as e:
        sys.exit(f"ERREUR : {e}")

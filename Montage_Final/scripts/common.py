"""Utilitaires partagés : chemins, journalisation, ffmpeg/ffprobe, encodeurs."""
import json
import logging
import os
import platform
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(os.environ.get("MONTAGE_ROOT", Path(__file__).resolve().parent.parent)).resolve()
DIRS = {
    "scripts": ROOT / "scripts",
    "ill": ROOT / "ressources" / "illustrations",
    "titres": ROOT / "ressources" / "titres",
    "audio": ROOT / "ressources" / "audio",
    "inter": ROOT / "intermediaires",
    "v": ROOT / "vertical_9x16",
    "h": ROOT / "horizontal_16x9",
    "rapport": ROOT / "rapport",
}

log = logging.getLogger("montage")


class MontageError(RuntimeError):
    """Erreur lisible pour l'utilisateur (commande échouée, dépendance absente...)."""


def ensure_dirs():
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)


def setup_logging(verbose=False):
    ensure_dirs()
    if log.handlers:
        return
    log.setLevel(logging.DEBUG)
    fh = logging.FileHandler(DIRS["rapport"] / "execution.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    fh.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG if verbose else logging.INFO)
    sh.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(fh)
    log.addHandler(sh)


def run(cmd, cwd=None, check=True):
    """Exécute une commande (liste d'arguments, jamais via un shell)."""
    cmd = [str(c) for c in cmd]
    log.debug("RUN %s (cwd=%s)", " ".join(cmd), cwd)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        tail = (p.stderr or "")[-1800:]
        raise MontageError(f"Commande échouée ({cmd[0]}), code {p.returncode} :\n{tail}")
    return p


def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def probe(path):
    """Métadonnées utiles d'un média (ffprobe)."""
    p = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", path])
    j = json.loads(p.stdout)
    info = {"path": str(path), "duration": float(j["format"].get("duration", 0)),
            "video": None, "audio": None}
    for s in j["streams"]:
        if s["codec_type"] == "video" and not info["video"] and \
                s.get("disposition", {}).get("attached_pic", 0) == 0:
            w, h = int(s["width"]), int(s["height"])
            rot = 0
            for sd in s.get("side_data_list", []):
                if "rotation" in sd:
                    rot = int(sd["rotation"])
            if rot in (90, -90, 270, -270):
                w, h = h, w
            try:
                fps = float(Fraction(s.get("avg_frame_rate") or s["r_frame_rate"]))
            except (ZeroDivisionError, ValueError):
                fps = 30.0
            info["video"] = {"w": w, "h": h, "fps": round(fps, 3),
                             "codec": s["codec_name"], "pix_fmt": s.get("pix_fmt")}
        elif s["codec_type"] == "audio" and not info["audio"]:
            info["audio"] = {"codec": s["codec_name"],
                             "rate": int(s.get("sample_rate", 0)),
                             "channels": int(s.get("channels", 0))}
    return info


_ENC_CACHE = {}


def encoder_args(prefer_gpu=True, crf=18, preset="medium"):
    """H.264 matériel si réellement utilisable (test d'encodage réel), sinon x264."""
    key = (prefer_gpu, crf, preset)
    if key in _ENC_CACHE:
        return _ENC_CACHE[key]
    args = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
    if prefer_gpu:
        for name, extra in (("h264_nvenc", ["-preset", "p5", "-rc", "vbr", "-cq", str(crf + 2), "-b:v", "0"]),
                            ("h264_qsv", ["-global_quality", str(crf + 2)])):
            t = run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2",
                     "-c:v", name, "-f", "null", "-"], check=False)
            if t.returncode == 0:
                log.info("Encodeur matériel utilisable : %s", name)
                args = ["-c:v", name] + extra
                break
        else:
            log.info("Aucun encodeur matériel utilisable -> repli sur libx264 (logiciel)")
    _ENC_CACHE[key] = args
    return args


def ass_font(preferred=None):
    """Nom de police pour libass (épaisse, moderne) selon l'OS."""
    if preferred:
        return preferred
    if platform.system() == "Windows":
        return "Arial Black"
    p = run(["fc-list", ":", "family"], check=False)
    fams = (p.stdout or "") if p.returncode == 0 else ""
    for cand in ("Montserrat", "Inter", "Poppins", "DejaVu Sans"):
        if cand.lower() in fams.lower():
            return cand
    return "Arial"


def find_font_file(bold=True):
    """Chemin d'une police TTF/OTF épaisse pour Pillow."""
    cands = []
    if os.environ.get("MONTAGE_FONT"):
        cands.append(os.environ["MONTAGE_FONT"])
    cands += [r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\segoeuib.ttf",
              r"C:\Windows\Fonts\arialbd.ttf",
              "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
              "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Black.ttf"]
    for c in cands:
        if Path(c).exists():
            return c
    raise MontageError("Aucune police trouvée : définir la variable MONTAGE_FONT vers un .ttf gras.")

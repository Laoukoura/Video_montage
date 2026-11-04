#!/usr/bin/env python3
"""Voix off : synthèse neuronale française masculine (Piper, voix « fr_FR-tom-medium »).

Chaque réplique est générée séparément pour pouvoir caler précisément les plans
sur la narration. Sortie : build/vo_XX.wav + build/vo.json (durées).
Le modèle (.onnx + .onnx.json) est cherché dans ../voix/ ou via --model.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"

# Texte prononcé (orthographe adaptée à la phonétique) -> identifiant de plan
LIGNES = [
    ("hook",     "Et si ton téléphone devenait un vrai studio de montage ?"),
    ("claude",   "Avec Claude AI, l'intelligence artificielle devient ton assistant de réalisation."),
    ("montage",  "Script, découpage, sous-titres, musique, effets… tu apprends à monter des vidéos professionnelles, de A à Z."),
    ("mobile",   "Sans ordinateur. Sans logiciel compliqué. Cent pour cent sur téléphone."),
    ("publier",  "Et tu repars avec des vidéos prêtes à publier sur TikTok, Reels et WhatsApp."),
    ("afrique",  "Rejoins une formation pratique, en direct, avec des créateurs de toute l'Afrique."),
    ("cta",      "Les places sont limitées. Inscris-toi dès maintenant, et maîtrise le montage vidéo avec Claude AI !"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(ROOT / "voix" / "fr_FR-tom-medium.onnx"))
    ap.add_argument("--speed", type=float, default=0.96, help="length_scale Piper (<1 = plus rapide)")
    a = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    out = []
    for i, (key, txt) in enumerate(LIGNES):
        wav = BUILD / f"vo_{i:02d}.wav"
        subprocess.run([sys.executable, "-m", "piper", "-m", a.model, "-f", str(wav),
                        "--length-scale", str(a.speed), "--noise-scale", "0.6",
                        "--noise-w-scale", "0.7"],
                       input=txt.encode(), check=True, capture_output=True)
        with wave.open(str(wav)) as w:
            d = w.getnframes() / w.getframerate()
        out.append({"key": key, "text": txt, "wav": wav.name, "dur": round(d, 3)})
        print(f"{key:8s} {d:5.2f}s  {txt}")
    (BUILD / "vo.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("total voix :", round(sum(o["dur"] for o in out), 2), "s")


if __name__ == "__main__":
    main()

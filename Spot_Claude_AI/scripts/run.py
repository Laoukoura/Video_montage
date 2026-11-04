#!/usr/bin/env python3
"""Pipeline complet : voix off -> bande-son -> rendu image -> assemblage final.

    python run.py            # tout
    python run.py --skip-voice
Sortie : ../sortie/Spot_Claude_AI_9x16_1080p.mp4 (1080x1920, 30 i/s, H.264 + AAC, -14 LUFS)
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "sortie" / "Spot_Claude_AI_9x16_1080p.mp4"


def step(*args):
    print("==>", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=HERE, check=True)


def main():
    if "--skip-voice" not in sys.argv:
        step("narration.py")
    step("audio.py")
    step("video.py", str(ROOT / "build" / "video.mp4"))
    OUT.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ROOT / "build" / "video.mp4"),
                    "-i", str(ROOT / "build" / "mix.wav"),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "10M",
                    "-bufsize", "20M", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart",
                    "-metadata", "title=Maîtrise le montage vidéo avec Claude AI", str(OUT)], check=True)
    print("OK ->", OUT)


if __name__ == "__main__":
    main()

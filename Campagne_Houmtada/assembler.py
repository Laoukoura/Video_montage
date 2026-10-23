#!/usr/bin/env python3
"""Assemble les 6 scènes du spot Houmtada House (30 s, 9:16) en une seule vidéo.

Entrée : un dossier contenant scene1.mp4 ... scene6.mp4 (plans déjà générés / tournés).
Chaque scène est coupée à sa durée du storyboard, les transitions tombent aux temps exacts
(3, 7, 12, 18, 25 s), puis textes, logo, musique, effets sonores et normalisation -14 LUFS.

Dépendances : ffmpeg/ffprobe dans le PATH.
Exemple :
  python assembler.py plans/ houmtada_30s.mp4 --musique musique.mp3 --sfx sfx.wav \
      --logo logo.png --police Montserrat-Bold.ttf
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

W, H, FPS = 1080, 1920, 30

# (durée en s, transition vers la scène suivante, durée de la transition)
SCENES = [
    (3.0, "fade", 0.2),       # 1 -> 2 : raccord mouvement
    (4.0, "wipeup", 0.4),     # 2 -> 3 : volet par la vague de yaourt
    (5.0, None, 0.0),         # 3 -> 4 : coupe franche
    (6.0, "fade", 0.5),       # 4 -> 5 : fondu enchaîné doux
    (7.0, "fadewhite", 0.3),  # 5 -> 6 : fondu au blanc crème
    (5.0, None, 0.0),
]
TOTAL = sum(s[0] for s in SCENES)

# (début, fin, texte, taille, couleur, y) ; y en expression drawtext
TEXTES = [
    (9.5, 11.5, "HOUMTADA HOUSE", 54, "white", "h*0.14"),
    (12.5, 17.5, "Fait main. Fruits frais.", 62, "white", "h*0.14"),
    (26.3, 30.0, "La fraîcheur prend vie", 64, "0xD7141A", "h*0.27"),
    (27.3, 30.0, "Découvrez votre plaisir fruité.", 50, "0x222222", "h*0.32"),
]
LIVRAISON = (27.8, 30.0, "Livraison partout à N'Djamena · 63 91 46 98", 36, "white", "h*0.72")


def run(cmd):
    subprocess.run(cmd, check=True)


def duree(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(out)["format"]["duration"])


def esc(txt):
    """Échappement pour drawtext (texte entre apostrophes dans le filtergraph)."""
    return (txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")
            .replace("%", "\\%"))


def esc_path(p):
    return str(Path(p).resolve()).replace("\\", "/").replace(":", "\\:")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier", type=Path, help="dossier contenant scene1.mp4 ... scene6.mp4")
    ap.add_argument("sortie", type=Path)
    ap.add_argument("--musique", type=Path)
    ap.add_argument("--sfx", type=Path, help="piste d'effets sonores calée sur 30 s")
    ap.add_argument("--logo", type=Path, help="logo réel détouré (PNG transparent)")
    ap.add_argument("--police", type=Path, help="fichier .ttf/.otf pour les textes")
    ap.add_argument("--sans-textes", action="store_true")
    ap.add_argument("--option-livraison", action="store_true")
    ap.add_argument("--crf", type=int, default=17)
    a = ap.parse_args()

    clips = [a.dossier / f"scene{i}.mp4" for i in range(1, 7)]
    manquants = [c for c in clips if not c.exists()]
    if manquants:
        sys.exit("Plans manquants : " + ", ".join(map(str, manquants)))

    cmd = ["ffmpeg", "-y", "-hide_banner"]
    for c in clips:
        cmd += ["-i", str(c)]
    n = len(clips)
    idx_musique = idx_sfx = idx_logo = None
    for opt in ("musique", "sfx", "logo"):
        p = getattr(a, opt)
        if p:
            cmd += (["-loop", "1"] if opt == "logo" else []) + ["-i", str(p)]
            if opt == "musique":
                idx_musique = n
            elif opt == "sfx":
                idx_sfx = n
            else:
                idx_logo = n
            n += 1

    f = []
    # 1. normalisation + découpe ; un plan trop court est prolongé par sa dernière image
    for i, (c, (d, _, t)) in enumerate(zip(clips, SCENES)):
        besoin = d + t
        manque = max(0.0, besoin - duree(c))
        if manque > 0.01:
            print(f"Attention : {c.name} trop court de {manque:.2f} s, dernière image prolongée")
        f.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"fps={FPS},setsar=1,format=yuv420p,"
            f"tpad=stop_mode=clone:stop_duration={manque + 0.1:.3f},"
            f"trim=duration={besoin:.3f},setpts=PTS-STARTPTS,settb=AVTB[s{i}]")

    # 2. transitions : chaque scène i dure d_i + t_i, la transition démarre à la fin de d_i
    prec, cumul = "s0", 0.0
    for i in range(1, len(SCENES)):
        d, trans, t = SCENES[i - 1]
        cumul += d
        out = f"x{i}"
        if trans:
            f.append(f"[{prec}][s{i}]xfade=transition={trans}:duration={t}:offset={cumul:.3f}[{out}]")
        else:
            f.append(f"[{prec}][s{i}]concat=n=2:v=1:a=0,settb=AVTB[{out}]")
        prec = out

    # 3. logo + textes
    if idx_logo is not None and not a.sans_textes:
        f.append(f"[{idx_logo}:v]scale={int(W * 0.62)}:-1,format=rgba,"
                 f"fade=in:st=25.5:d=0.5:alpha=1,trim=duration={TOTAL}[logo]")
        f.append(f"[{prec}][logo]overlay=(W-w)/2:H*0.10:enable='gte(t,25.5)':shortest=1[vl]")
        prec = "vl"
    if not a.sans_textes:
        police = f"fontfile='{esc_path(a.police)}':" if a.police else ""
        textes = TEXTES + ([LIVRAISON] if a.option_livraison else [])
        dt = []
        for texte in textes:
            deb, fin, txt, taille, coul, y = texte
            boite = ":box=1:boxcolor=0xD7141A:boxborderw=24" if texte is LIVRAISON else ""
            dt.append(
                f"drawtext={police}text='{esc(txt)}':fontsize={taille}:fontcolor={coul}:"
                f"x=(w-text_w)/2:y={y}{boite}:enable='between(t,{deb},{fin})':"
                f"alpha='min(1,(t-{deb})/0.3)'")
        f.append(f"[{prec}]" + ",".join(dt) + "[vt]")
        prec = "vt"
    f.append(f"[{prec}]trim=duration={TOTAL},setpts=PTS-STARTPTS[vout]")

    # 4. audio : musique + effets, fondu de sortie, -14 LUFS
    pistes = [k for k in (idx_musique, idx_sfx) if k is not None]
    if pistes:
        for j, k in enumerate(pistes):
            f.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,"
                     f"atrim=duration={TOTAL},asetpts=PTS-STARTPTS,apad=whole_dur={TOTAL}[a{j}]")
        mix = ("".join(f"[a{j}]" for j in range(len(pistes)))
               + f"amix=inputs={len(pistes)}:normalize=0," if len(pistes) > 1 else "[a0]")
        f.append(f"{mix}afade=t=out:st={TOTAL - 1}:d=1,"
                 f"loudnorm=I=-14:TP=-1:LRA=11,aresample=48000[aout]")

    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]"]
    if pistes:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "320k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-profile:v", "high",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", str(TOTAL),
            "-movflags", "+faststart", str(a.sortie)]
    run(cmd)
    print(f"OK : {a.sortie} ({duree(a.sortie):.2f} s)")


if __name__ == "__main__":
    main()

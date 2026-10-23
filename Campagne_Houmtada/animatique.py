#!/usr/bin/env python3
"""Animatique du spot Houmtada House : maquette 30 s montée avec les photos de référence.

Sert à valider le rythme, les temps des textes et les transitions AVANT de payer la
génération vidéo ou le tournage. Chaque scène est un plan fixe animé (zoom lent) tiré
des captures de references/, avec un cartouche « ANIMATIQUE · Sn ». La scène 5 (dégustation)
n'a pas de référence : elle affiche « PLAN À TOURNER ». La musique est un guide de tempo
à 120 BPM (une pulsation par temps, accents aux transitions), à remplacer par la vraie musique.

Les plans produits (plans_animatique/scene1..6.mp4) passent ensuite par assembler.py.
Exemple :
  python animatique.py animatique_30s.mp4 --police Montserrat-Bold.ttf
"""
import argparse
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
REF = ICI / "references"
W, H, FPS = 1080, 1920, 30

# fichier, recadrage (x, y, l, h) qui exclut l'interface TikTok, zoom début -> fin, assombrir
B1 = ("01_bol_kiwi_fraise_raisin.jpg", (0, 560, 510, 460))
B1_COUCHES = ("01_bol_kiwi_fraise_raisin.jpg", (20, 800, 470, 220))
B2 = ("02_gamme_bols_granola.jpg", (0, 790, 680, 240))
G3 = ("03_gobelet_salade_fruits.jpg", (0, 230, 720, 1000))
E4 = ("04_etiquette_couvercle.jpg", (0, 150, 750, 1050))
G5 = ("05_gobelet_parfait_chocolat.jpg", (20, 470, 490, 560))

# scène -> liste de plans (référence, durée, zoom début, zoom fin, assombrir)
SCENES = {
    1: ("Le choc visuel", [(G3, 3.4, 1.0, 1.45, True)]),
    2: ("L'explosion de fraîcheur", [(B1, 4.6, 1.3, 1.0, False)]),
    3: ("La révélation", [(E4, 5.2, 1.0, 1.15, False)]),
    4: ("La signature gourmande", [(B1_COUCHES, 2.0, 1.0, 1.1, False),
                                   (B2, 2.0, 1.1, 1.0, False),
                                   (G5, 2.7, 1.0, 1.1, False)]),
    5: ("Le plaisir à partager", [(B1, 7.5, 1.0, 1.05, True)]),
    6: ("La signature finale", [(E4, 5.2, 1.0, 1.1, False)]),
}


def run(cmd):
    subprocess.run(cmd, check=True)


def esc(txt):
    return txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")


def plan(ref, duree, z0, z1, sombre, cartouche, sortie, police, a_tourner=False):
    fichier, (x, y, l, h) = ref
    f = (f"[0:v]crop={l}:{h}:{x}:{y},split[a][b];"
         f"[a]scale={2 * W}:{2 * H}:force_original_aspect_ratio=increase,crop={2 * W}:{2 * H},"
         f"boxblur=40:2,eq=brightness=-0.15[fond];"
         f"[b]scale={2 * W}:{2 * H}:force_original_aspect_ratio=decrease[av];"
         f"[fond][av]overlay=(W-w)/2:(H-h)/2,")
    n = int(round(duree * FPS))
    f += (f"zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
          f"d=1:s={W}x{H}:fps={FPS}")
    if sombre:
        f += ",eq=brightness=-0.25:saturation=1.2,vignette=PI/3"
    fp = f"fontfile='{str(Path(police).resolve()).replace(chr(92), '/').replace(':', chr(92) + ':')}':" if police else ""
    f += (f",drawtext={fp}text='{esc(cartouche)}':fontsize=34:fontcolor=white:"
          f"box=1:boxcolor=black@0.55:boxborderw=14:x=40:y=h*0.05")
    if a_tourner:
        f += (f",drawtext={fp}text='PLAN À TOURNER':fontsize=84:fontcolor=white:"
              f"box=1:boxcolor=0xD7141A@0.9:boxborderw=30:x=(w-text_w)/2:y=h*0.45,"
              f"drawtext={fp}text='Dégustation à deux · bol visible':fontsize=44:fontcolor=white:"
              f"x=(w-text_w)/2:y=h*0.53")
    f += ",format=yuv420p[v]"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(REF / fichier),
         "-filter_complex", f, "-map", "[v]", "-t", f"{duree:.3f}", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "18", "-preset", "fast", str(sortie)])


def guide_tempo(sortie, total=30.0):
    """Pulsation 120 BPM + petit « tic » à contretemps + accent grave aux transitions."""
    temps = "mod(t,0.5)"
    kick = f"0.7*sin(2*PI*(50+140*exp(-30*{temps}))*{temps})*exp(-10*{temps})"
    tic = "0.12*sin(2*PI*3200*t)*exp(-90*mod(t+0.25,0.5))"
    accents = "+".join(
        f"0.6*sin(2*PI*90*(t-{s}))*exp(-4*(t-{s}))*gte(t,{s})" for s in (3, 7, 12, 18, 25, 26))
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"aevalsrc='{kick}+{tic}+{accents}':s=48000:d={total}",
         "-af", "volume=0.6", str(sortie)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sortie", type=Path)
    ap.add_argument("--police", type=Path, help="fichier .ttf/.otf (sinon police système)")
    ap.add_argument("--musique", type=Path, help="vraie musique (sinon guide de tempo 120 BPM)")
    ap.add_argument("--option-livraison", action="store_true")
    a = ap.parse_args()

    dossier = ICI / "plans_animatique"
    dossier.mkdir(exist_ok=True)
    for num, (titre, plans) in SCENES.items():
        cartouche = f"ANIMATIQUE · S{num} {titre}"
        morceaux = []
        for k, (ref, duree, z0, z1, sombre) in enumerate(plans):
            sortie = dossier / (f"scene{num}.mp4" if len(plans) == 1 else f"scene{num}_{k}.mp4")
            plan(ref, duree, z0, z1, sombre, cartouche, sortie, a.police, a_tourner=(num == 5))
            morceaux.append(sortie)
        if len(morceaux) > 1:
            liste = dossier / f"scene{num}.txt"
            liste.write_text("".join(f"file '{m.name}'\n" for m in morceaux))
            run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
                 "-c", "copy", str(dossier / f"scene{num}.mp4")])
        print(f"Scène {num} prête")

    musique = a.musique
    if not musique:
        musique = dossier / "guide_tempo.wav"
        guide_tempo(musique)

    cmd = [sys.executable, str(ICI / "assembler.py"), str(dossier), str(a.sortie), "--musique", str(musique)]
    if a.police:
        cmd += ["--police", str(a.police)]
    if a.option_livraison:
        cmd.append("--option-livraison")
    run(cmd)


if __name__ == "__main__":
    main()

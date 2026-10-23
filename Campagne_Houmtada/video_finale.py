#!/usr/bin/env python3
"""Version publiable du spot Houmtada House, montée avec les photos réelles de references/.

Contrairement à l'animatique : pas de cartouches, la scène 5 utilise les vraies photos,
plan de fin avec l'étiquette réelle détourée, musique de fond générée (120 BPM, fa majeur)
et étalonnage commun. Les plans passent ensuite par assembler.py (transitions, textes, -14 LUFS).

Exemple :
  python video_finale.py HOUMTADA_30s.mp4 --police Inter-Bold.otf
  python video_finale.py HOUMTADA_30s.mp4 --musique musique_sous_licence.mp3
"""
import argparse
import subprocess
import sys
from pathlib import Path

from animatique import B1, B1_COUCHES, B2, E4, G3, G5, REF, esc

ICI = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
K = 1.5  # suréchantillonnage pour des zooms sans escalier
ROUGE = "0xD7141A"
ETALONNAGE = "eq=contrast=1.06:saturation=1.18:gamma=0.98,unsharp=5:5:0.6"

# scène -> plans (référence, durée, zoom début, zoom fin, effet)
SCENES = {
    1: [(G3, 3.4, 1.0, 1.45, "eveil")],
    2: [(B1, 4.6, 1.3, 1.0, None)],
    3: [(E4, 5.2, 1.0, 1.15, None)],
    4: [(B1_COUCHES, 2.0, 1.0, 1.12, None), (B2, 2.0, 1.12, 1.0, None), (G5, 2.7, 1.0, 1.12, None)],
    5: [(G5, 3.7, 1.15, 1.0, "partage"), (B2, 3.8, 1.0, 1.12, "partage")],
}
ETIQUETTE = ("04_etiquette_couvercle.jpg", (5, 285, 840, 920))
# zone du bord droit de l'étiquette recouverte par les icônes TikTok (coordonnées du recadrage)
ICONES = (748, 180, 92, 720)


def run(cmd):
    subprocess.run(cmd, check=True)


def fontopt(police):
    if not police:
        return ""
    p = str(Path(police).resolve()).replace("\\", "/").replace(":", "\\:")
    return f"fontfile='{p}':"


def plan(ref, duree, z0, z1, effet, sortie, police):
    fichier, (x, y, l, h) = ref
    n = int(round(duree * FPS))
    f = (f"[0:v]crop={l}:{h}:{x}:{y},split[a][b];"
         f"[a]scale={int(K * W)}:{int(K * H)}:force_original_aspect_ratio=increase,"
         f"crop={int(K * W)}:{int(K * H)},boxblur=40:2,eq=brightness=-0.12[fond];"
         f"[b]scale={int(K * W)}:{int(K * H)}:force_original_aspect_ratio=decrease:flags=lanczos[av];"
         f"[fond][av]overlay=(W-w)/2:(H-h)/2,"
         f"zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
         f"d=1:s={W}x{H}:fps={FPS},{ETALONNAGE}")
    if effet == "eveil":  # sortie du noir : le produit « prend vie »
        f += ",eq=brightness='-0.45+0.45*min(1,t/1.6)':eval=frame,vignette=PI/4"
    if effet == "partage":
        f += (f",drawtext={fontopt(police)}text='{esc('À partager en famille')}':fontsize=66:"
              f"fontcolor=white:shadowcolor=black@0.6:shadowx=3:shadowy=3:"
              f"x=(w-text_w)/2:y=h*0.14:alpha='min(1,t/0.4)'")
    f += ",format=yuv420p[v]"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(REF / ref[0]),
         "-filter_complex", f, "-map", "[v]", "-t", f"{duree:.3f}", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-preset", "fast", str(sortie)])


def plan_final(sortie, police, duree=5.2):
    """Fond crème sur fruits flous, étiquette réelle détourée en ovale, nom de marque en haut."""
    fichier, (x, y, l, h) = ETIQUETTE
    ix, iy, iw, ih = ICONES
    d = "pow((X-W/2)/(W/2),2)+pow((Y-H/2)/(H/2),2)"
    lw = 560
    n = int(round(duree * FPS))
    fp = fontopt(police)
    f = (f"[0:v]crop=720:1000:0:230,scale={W}:{H}:force_original_aspect_ratio=increase,"
         f"crop={W}:{H},boxblur=30:3[f0];"
         f"color=c=0xFFF4E6@0.82:s={W}x{H},format=rgba[creme];"
         f"[f0][creme]overlay,format=rgba[fond];"
         # les icônes sont recouvertes en étirant la bande d'étiquette juste à leur gauche
         f"[1:v]crop={l}:{h}:{x}:{y},split[lab][bd];"
         f"[bd]crop=10:{ih}:{ix - 10}:{iy},scale={iw}:{ih}[bande];"
         f"[lab][bande]overlay={ix}:{iy},"
         f"scale={lw}:-2:flags=lanczos,format=rgba,"
         f"geq=r='if(gte({d},0.955),215,r(X,Y))':g='if(gte({d},0.955),20,g(X,Y))':"
         f"b='if(gte({d},0.955),26,b(X,Y))':a='255*lte({d},1)'[eti];"
         f"[fond][eti]overlay=(W-w)/2:H*0.37,"
         f"drawtext={fp}text='HOUMTADA HOUSE':fontsize=92:fontcolor={ROUGE}:"
         f"x=(w-text_w)/2:y=h*0.155:alpha='min(1,t/0.5)',"
         f"zoompan=z='1+0.06*min(1,on/({n}-60))':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
         f"d=1:s={W}x{H}:fps={FPS},format=yuv420p[v]")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(REF / "03_gobelet_salade_fruits.jpg"),
         "-loop", "1", "-i", str(REF / fichier), "-filter_complex", f, "-map", "[v]",
         "-t", f"{duree:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "16", "-preset", "fast",
         str(sortie)])


def musique(sortie, total=30.0):
    """Groove léger 120 BPM en fa majeur (F, Dm, Bb, C), intro 0-3 s, couplet doux 18-25 s."""
    def accord(f, dm, bb, c):
        return (f"if(lt(mod(t,8),2),{f},if(lt(mod(t,8),4),{dm},if(lt(mod(t,8),6),{bb},{c})))")
    racine = accord(87.31, 73.42, 58.27, 65.41)
    notes = [accord(349.23, 293.66, 233.08, 261.63), accord(440.0, 349.23, 293.66, 329.63),
             accord(523.25, 440.0, 349.23, 392.0)]
    groove = "gte(t,3)"
    doux = "(1-0.45*between(t,18,25))"
    kick = f"0.9*sin(2*PI*(48+150*exp(-28*mod(t,0.5)))*mod(t,0.5))*exp(-9*mod(t,0.5))*{groove}*(1-0.7*between(t,18,25))"
    basse = f"0.38*sin(2*PI*{racine}*t)*(0.35+0.65*exp(-4*mod(t,0.5)))*{groove}"
    nappe = "+".join(f"0.05*sin(2*PI*{n}*t)" for n in notes)
    arpege = (f"0.13*sin(2*PI*if(eq(mod(floor(t*4),3),0),{notes[0]},if(eq(mod(floor(t*4),3),1),{notes[1]},{notes[2]}))*2*t)"
              f"*exp(-14*mod(t,0.25))*{groove}*{doux}")
    impact = "0.9*sin(2*PI*(35+90*exp(-6*t))*t)*exp(-2.2*t)"
    signature = ("0.25*sin(2*PI*698.46*(t-26))*exp(-5*(t-26))*gte(t,26)"
                 "+0.25*sin(2*PI*1046.5*(t-26.25))*exp(-4*(t-26.25))*gte(t,26.25)")
    expr = f"({kick}+{basse}+{nappe}*min(1,t/2)+{arpege}+{impact}+{signature})*0.75"
    expr2 = expr.replace("*t)", "*(t+0.0004))", 3)  # léger décalage = largeur stéréo
    f = (f"aevalsrc='{expr}|{expr2}':s=48000:d={total}[mel];"
         f"anoisesrc=c=white:a=0.5:d={total}:r=48000,highpass=f=7000,"
         f"volume='0.5*exp(-55*mod(t,0.25))*gte(t,3)':eval=frame,pan=stereo|c0=c0|c1=c0[hat];"
         f"anoisesrc=c=pink:a=0.6:d={total}:r=48000,bandpass=f=1800:w=1600,"
         f"volume='0.7*exp(-22*mod(t-0.5,1))*gte(t,3)*gte(mod(t,1),0.5)':eval=frame,"
         f"pan=stereo|c0=c0|c1=c0[clap];"
         f"anoisesrc=c=pink:a=0.5:d={total}:r=48000,bandpass=f=900:w=1200,"
         f"volume='0.5*(exp(-5*abs(t-3))+exp(-5*abs(t-7))+exp(-5*abs(t-25)))':eval=frame,"
         f"pan=stereo|c0=c0|c1=c0[souffle];"
         f"[mel][hat][clap][souffle]amix=inputs=4:normalize=0,"
         f"aecho=0.6:0.4:250:0.18,alimiter=limit=0.9[a]")
    run(["ffmpeg", "-v", "error", "-y", "-filter_complex", f, "-map", "[a]", str(sortie)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sortie", type=Path)
    ap.add_argument("--police", type=Path, help="fichier .ttf/.otf (sinon police système)")
    ap.add_argument("--musique", type=Path, help="musique sous licence (sinon musique générée)")
    a = ap.parse_args()

    dossier = ICI / "plans_finale"
    dossier.mkdir(exist_ok=True)
    for num, plans in SCENES.items():
        morceaux = []
        for k, (ref, duree, z0, z1, effet) in enumerate(plans):
            s = dossier / (f"scene{num}.mp4" if len(plans) == 1 else f"scene{num}_{k}.mp4")
            plan(ref, duree, z0, z1, effet, s, a.police)
            morceaux.append(s)
        if len(morceaux) > 1:
            liste = dossier / f"scene{num}.txt"
            liste.write_text("".join(f"file '{m.name}'\n" for m in morceaux))
            run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
                 "-c", "copy", str(dossier / f"scene{num}.mp4")])
        print(f"Scène {num} prête")
    plan_final(dossier / "scene6.mp4", a.police)
    print("Scène 6 prête")

    zik = a.musique
    if not zik:
        zik = dossier / "musique.wav"
        musique(zik)
    cmd = [sys.executable, str(ICI / "assembler.py"), str(dossier), str(a.sortie),
           "--musique", str(zik), "--option-livraison"]
    if a.police:
        cmd += ["--police", str(a.police)]
    run(cmd)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Montage automatique façon Short/Reel/TikTok à partir d'une vidéo brute.

Étapes (un seul encodage vidéo final, donc rapide) :
  1. détection des silences  -> jump cuts (suppression des blancs)
  2. recadrage 9:16 (1080x1920), zoom "punch-in" alterné à chaque coupe
  3. transcription mot à mot (faster-whisper, optionnel) -> sous-titres karaoké ASS
  4. musique de fond avec ducking (baisse auto sous la voix) + loudnorm
  5. encodage H.264 (ou NVENC avec --gpu)

Dépendances : ffmpeg/ffprobe (obligatoire), faster-whisper (optionnel, pour les sous-titres)
Exemple :
  python3 montage.py in.mp4 out.mp4 --music zik.mp3 --lang fr
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)])
    return float(json.loads(out)["format"]["duration"])


# --------------------------------------------------------------------------- #
# 1. Silences -> segments à garder
# --------------------------------------------------------------------------- #
def detect_keep_segments(path, noise_db, min_silence, pad, min_keep):
    dur = probe_duration(path)
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}",
         "-f", "null", "-"],
        capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    keep, cur = [], 0.0
    for i, s in enumerate(starts):
        if s - cur > 0:
            keep.append((cur, s))
        cur = ends[i] if i < len(ends) else dur
    if cur < dur:
        keep.append((cur, dur))
    # marge autour de la parole pour ne pas couper les attaques/fins de mots
    padded = [(max(0, a - pad), min(dur, b + pad)) for a, b in keep]
    merged = []
    for a, b in padded:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    merged = [(a, b) for a, b in merged if b - a >= min_keep]
    return merged or [(0.0, dur)]


# --------------------------------------------------------------------------- #
# 2/4. Graphe ffmpeg
# --------------------------------------------------------------------------- #
def build_graph(segs, w, h, zoom, with_video, music, duck, ass_path, fade=0.012):
    """Retourne (filter_complex, label_vidéo|None, label_audio)."""
    n = len(segs)
    lines = []
    for i, (a, b) in enumerate(segs):
        d = b - a
        if with_video:
            v = (f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,"
                 f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                 f"crop={w}:{h}")
            if i % 2 == 1 and zoom > 1:  # punch-in sur une coupe sur deux
                v += f",crop=iw/{zoom}:ih/{zoom},scale={w}:{h}:flags=bicubic"
            lines.append(v + f",setsar=1[v{i}]")
        lines.append(
            f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={fade},afade=t=out:st={max(d - fade, 0):.3f}:d={fade}[a{i}]")
    if with_video:
        vin = "".join(f"[v{i}]" for i in range(n))
        lines.append(f"{vin}concat=n={n}:v=1:a=0[vcat]")
    ain = "".join(f"[a{i}]" for i in range(n))
    lines.append(f"{ain}concat=n={n}:v=0:a=1[voice]")

    vlabel = None
    if with_video:
        vlabel = "vcat"
        if ass_path:
            esc = str(ass_path).replace("\\", "/").replace(":", r"\:")
            lines.append(f"[vcat]ass='{esc}'[vout]")
            vlabel = "vout"

    if music:
        if duck:
            lines.append("[voice]asplit=2[vmix][vsc]")
            lines.append("[1:a]volume=0.5[m]")
            lines.append("[m][vsc]sidechaincompress=threshold=0.03:ratio=8:"
                         "attack=20:release=400[mduck]")
            lines.append("[vmix][mduck]amix=inputs=2:duration=first:normalize=0[mix]")
        else:
            lines.append("[1:a]volume=0.15[m]")
            lines.append("[voice][m]amix=inputs=2:duration=first:normalize=0[mix]")
        alabel = "mix"
    else:
        alabel = "voice"
    lines.append(f"[{alabel}]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    return ";\n".join(lines), vlabel, "aout"


# --------------------------------------------------------------------------- #
# 3. Sous-titres karaoké
# --------------------------------------------------------------------------- #
def transcribe_words(wav, lang, model_size):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("! faster-whisper absent : pas de sous-titres "
              "(pip install faster-whisper)", file=sys.stderr)
        return []
    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(str(wav), language=lang, word_timestamps=True,
                                   vad_filter=True)
    return [(w.start, w.end, w.word.strip())
            for s in segments for w in (s.words or []) if w.word.strip()]


def ts(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_ass(words, path, w, h, font, size, words_per_line, uppercase,
              color_on="&H0000E5FF", color_off="&H00FFFFFF"):
    """Une ligne = N mots ; le mot en cours se remplit (\\kf) en jaune."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: K,{font},{size},{color_on},{color_off},&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,6,2,2,60,60,{int(h * 0.22)},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    out = [head]
    for i in range(0, len(words), words_per_line):
        grp = words[i:i + words_per_line]
        start = grp[0][0]
        end = grp[-1][1]
        txt = ""
        for j, (s, e, t) in enumerate(grp):
            nxt = grp[j + 1][0] if j + 1 < len(grp) else e
            cs = max(1, int(round((nxt - s) * 100)))
            txt += f"{{\\kf{cs}}}{t.upper() if uppercase else t} "
        out.append(f"Dialogue: 0,{ts(start)},{ts(end + 0.05)},K,,0,0,0,,{txt.strip()}\n")
    Path(path).write_text("".join(out), encoding="utf-8")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--music", help="fichier audio de fond (boucle auto)")
    ap.add_argument("--no-duck", action="store_true", help="pas de ducking, volume fixe")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--noise", type=float, default=-30, help="seuil silence en dB")
    ap.add_argument("--min-silence", type=float, default=0.35)
    ap.add_argument("--pad", type=float, default=0.08, help="marge gardée autour de la parole")
    ap.add_argument("--min-keep", type=float, default=0.4)
    ap.add_argument("--zoom", type=float, default=1.18, help="facteur de punch-in (1 = off)")
    ap.add_argument("--no-cuts", action="store_true", help="ne pas couper les silences")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--lang", default=None, help="langue (fr, en...) ; auto si omis")
    ap.add_argument("--whisper", default="small", help="tiny/base/small/medium")
    ap.add_argument("--font", default="Arial Black")
    ap.add_argument("--font-size", type=int, default=84)
    ap.add_argument("--words-per-line", type=int, default=3)
    ap.add_argument("--no-upper", action="store_true")
    ap.add_argument("--gpu", action="store_true", help="encodage NVENC")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preset", default="veryfast")
    a = ap.parse_args()

    src = Path(a.input)
    if a.no_cuts:
        segs = [(0.0, probe_duration(src))]
    else:
        segs = detect_keep_segments(src, a.noise, a.min_silence, a.pad, a.min_keep)
    total = sum(b - x for x, b in segs)
    print(f"{len(segs)} segments gardés, {total:.1f}s / {probe_duration(src):.1f}s")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ass = None
        if not a.no_captions:
            # audio seul coupé -> transcription (timestamps déjà alignés sur le montage)
            g, _, al = build_graph(segs, a.width, a.height, a.zoom, False, None, False, None)
            (td / "a.txt").write_text(g)
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                 "-filter_complex_script", str(td / "a.txt"), "-map", f"[{al}]",
                 "-ac", "1", "-ar", "16000", str(td / "cut.wav")])
            words = transcribe_words(td / "cut.wav", a.lang, a.whisper)
            if words:
                ass = td / "cap.ass"
                write_ass(words, ass, a.width, a.height, a.font, a.font_size,
                          a.words_per_line, not a.no_upper)

        g, vl, al = build_graph(segs, a.width, a.height, a.zoom, True,
                                a.music, not a.no_duck, ass)
        (td / "g.txt").write_text(g)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
               "-i", str(src)]
        if a.music:
            cmd += ["-stream_loop", "-1", "-i", a.music]
        cmd += ["-filter_complex_script", str(td / "g.txt"),
                "-map", f"[{vl}]", "-map", f"[{al}]", "-t", f"{total:.3f}"]
        if a.gpu:
            cmd += ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", str(a.crf)]
        else:
            cmd += ["-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf)]
        cmd += ["-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", a.output]
        run(cmd)
    print("OK ->", a.output)


if __name__ == "__main__":
    main()

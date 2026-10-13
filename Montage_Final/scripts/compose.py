"""Étapes F/G : montage audio-vidéo.

  cut_stage()  -> intermediaires/cut.mp4 : coupes sur mots, étalonnage léger, voix nettoyée
  compose()    -> export final d'UN format (cadrage, zooms, graphiques, sous-titres, SFX, musique)

Les deux formats partagent les coupes mais ont chacun leur profil : cadrage, zooms,
taille/position des sous-titres, cartes de titre, mots-clés et conclusion.
"""
from pathlib import Path

import common
import graphiques
import sfx
import sous_titres
from common import DIRS, MontageError, log, run

PROFILES = {
    "v": dict(w=1080, h=1920, fs=96, y=0.70, line_chars=13, group_words=4, upper=True, outline=8,
              shadow=3, zoom_k=1.0, callout=(0.5, 0.30), loud=-14, name="video_verticale_1080x1920.mp4",
              dir="v", vertical=True),
    "h": dict(w=1920, h=1080, fs=84, y=0.90, line_chars=24, group_words=6, upper=False, outline=5,
              shadow=2, zoom_k=0.6, callout=(0.95, 0.10), loud=-16, name="video_youtube_1920x1080.mp4",
              dir="h", vertical=False),
}


def s_expr(e):  # smoothstep (accélération + décélération naturelles)
    return f"(({e})*({e})*(3-2*({e})))"


def zoom_expr(zooms, k, cap):
    """Z(t) = 1 + somme d'enveloppes lissées ; amplitude plafonnée pour préserver la qualité."""
    terms = []
    for z in zooms:
        amp = min(z["amp"] * k, cap)
        if amp <= 0.005:
            continue
        up = s_expr(f"clip((t-{z['t0']:.3f})/{z['in']:.3f},0,1)")
        dn = s_expr(f"clip((t-{z['t1']:.3f})/{z['out']:.3f},0,1)")
        terms.append(f"{amp:.4f}*{up}*(1-{dn})")
    return "1" if not terms else "(1+" + "+".join(terms) + ")"


def grade_filter(luma):
    """Correction modérée : relève une image sombre, adoucit une image claire. Jamais agressive."""
    b = 0.0
    if luma is not None:
        if luma < 90:
            b = min(0.08, (90 - luma) / 700)
        elif luma > 170:
            b = -min(0.06, (luma - 170) / 800)
    return f"eq=contrast=1.04:saturation=1.06:brightness={b:.3f}"


VOICE_CHAIN = ("highpass=f=80,afftdn=nr=10:nf=-32,"
               "equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.0:g=2.5,"
               "acompressor=threshold=-20dB:ratio=2.5:attack=15:release=180:makeup=2")


def cut_stage(cuts, analyse, out=None, denoise=False):
    files = analyse["files"]
    ref = files[0]["video"]
    W, H, fps = ref["w"], ref["h"], ref["fps"]
    out = out or DIRS["inter"] / "cut.mp4"
    segs = cuts["segments"]
    n = len(segs)
    uses = {}
    for sg in segs:
        uses[sg["src"]] = uses.get(sg["src"], 0) + 1
    g = []
    for i, c in uses.items():  # normalisation de chaque rush puis duplication par segment
        g.append(f"[{i}:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=decrease,"
                 f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,split={c}"
                 + "".join(f"[nv{i}_{j}]" for j in range(c)))
        g.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,asplit={c}"
                 + "".join(f"[na{i}_{j}]" for j in range(c)))
    seen = {}
    for k, sg in enumerate(segs):
        i, a, b = sg["src"], sg["start"], sg["end"]
        j = seen.get(i, 0)
        seen[i] = j + 1
        d = b - a
        g.append(f"[nv{i}_{j}]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{k}]")
        g.append(f"[na{i}_{j}]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d=0.012,afade=t=out:st={max(d - 0.012, 0):.3f}:d=0.012[a{k}]")
    cat = "".join(f"[v{k}][a{k}]" for k in range(n))
    vf = grade_filter(files[0].get("luma")) + (",hqdn3d=2:2:3:3" if denoise else "")
    g += [f"{cat}concat=n={n}:v=1:a=1[cv][ca]", f"[cv]{vf}[vout]", f"[ca]{VOICE_CHAIN}[aout]"]
    gp = DIRS["inter"] / "graph_cut.txt"
    gp.write_text(";\n".join(g), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for f in files:
        cmd += ["-i", f["path"]]
    cmd += ["-filter_complex_script", gp, "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", out]
    log.info("Étape F : coupes + étalonnage + nettoyage voix -> %s", out)
    run(cmd)
    return out


def overlay_chain(cur, items, fps):
    """items : [(png, t0, dur, x_expr, y_expr)] -> lignes de graphe + label final."""
    lines = []
    for k, (idx, t0, dur, x, y) in enumerate(items):
        fd = min(0.3, dur / 3)
        lines.append(f"[{idx}:v]format=rgba,fade=t=in:st=0:d={fd}:alpha=1,"
                     f"fade=t=out:st={dur - fd:.3f}:d={fd}:alpha=1,setpts=PTS+{t0:.3f}/TB[o{k}]")
        lines.append(f"[{cur}][o{k}]overlay=x='{x}':y='{y}':eof_action=pass:"
                     f"enable='between(t,{t0:.3f},{t0 + dur:.3f})'[ov{k}]")
        cur = f"ov{k}"
    return lines, cur


def compose(fmt, cuts, plan, analyse, cut_path, out=None, music=None, focus_x=None,
            gpu=True, font=None, mode=None, crf=18):
    prof = PROFILES[fmt]
    W, H = prof["w"], prof["h"]
    src = analyse["files"][0]["video"]
    fps = src["fps"]
    inter = DIRS["inter"]
    out = Path(out or DIRS[prof["dir"]] / prof["name"])
    out.parent.mkdir(parents=True, exist_ok=True)
    tag = fmt
    outro = plan["outro"]
    extra = float(outro.get("extra", 3.0))
    total = cuts["duration"] + extra
    words = cuts["words"]

    # ---- sous-titres (ASS intégré + SRT complémentaire)
    ass_name = f"cap_{tag}.ass"
    n_ev = sous_titres.make_ass(words, inter / ass_name, prof, common.ass_font(font))
    sous_titres.make_srt(words, out.parent / "sous_titres.srt",
                         max_chars=prof["line_chars"] * 2, max_words=prof["group_words"] + 2)
    log.info("[%s] sous-titres : %d événements mot-par-mot", tag, n_ev)

    # ---- éléments graphiques
    pngs = []  # (fichier, t0, dur, x, y)
    t_title = plan["title_t"]
    p = inter / f"title_{tag}.png"
    graphiques.title_card(p, W, H, plan["title"], plan.get("subtitle"), prof["vertical"])
    slide = f"{18 if prof['vertical'] else 14}*(1-{s_expr(f'clip((t-{t_title:.3f})/0.4,0,1)')})"
    pngs.append((p, t_title, plan["title_dur"], "0", f"-{slide}"))
    cx, cy = prof["callout"]
    for k, c in enumerate(plan["callouts"]):
        p = inter / f"callout_{tag}_{k}.png"
        w, h = graphiques.callout(p, c["text"], c["icon"], H)
        x = f"{int(cx * W - w / 2)}" if cx == 0.5 else f"{int(cx * W - w)}"
        t0 = c["t"]
        y = f"{int(cy * H)}+24*(1-{s_expr(f'clip((t-{t0:.3f})/0.3,0,1)')})"
        pngs.append((p, t0, c["dur"], x, y))
    p = inter / f"outro_{tag}.png"
    graphiques.outro_card(p, W, H, outro.get("title") or plan["title"], outro.get("cta"),
                          outro.get("logo"), prof["vertical"])
    pngs.append((p, cuts["duration"] - 0.2, extra + 0.2, "0", "0"))

    # ---- sound design : positions déduites du plan
    ev = []
    if cuts["hook_end"]:
        ev.append((cuts["hook_end"] - 0.15, "whoosh", 0.55))
    ev.append((t_title, "whoosh", 0.45))
    ev += [(c["t"], "pop", 0.5) for c in plan["callouts"]]
    ev += [(z["t0"], "whoosh_down", 0.25) for z in plan["zooms"] if z["amp"] >= 0.15]
    ev.append((cuts["duration"] - 0.2, "impact", 0.5))
    ev.append((cuts["duration"] - 0.5, "whoosh", 0.4))
    sfx_path = inter / f"sfx_{tag}.wav"
    sfx.render(ev, total, sfx_path)

    # ---- cadrage
    sw, sh = src["w"], src["h"]
    k0 = max(W / sw, H / sh)
    aspect_src, aspect_dst = sw / sh, W / H
    if mode is None:
        if abs(aspect_src / aspect_dst - 1) < 0.04:
            mode = "cover"
        elif prof["vertical"] and aspect_src > 1:
            mode = "cover" if k0 <= 1.6 else "blurfit"   # évite un fort agrandissement
        elif not prof["vertical"] and aspect_src < 1:
            mode = "blurfit"
        else:
            mode = "cover"
    cap = max(0.0, 1.6 / max(k0 if mode == "cover" else W / sw, 1.0) - 1)
    Z = zoom_expr(plan["zooms"], prof["zoom_k"], cap)
    fx = focus_x if focus_x is not None else (analyse["files"][0].get("face_x") or 0.5)
    log.info("[%s] cadrage=%s, facteur de base=%.2f, zoom max=+%.0f%%, focus x=%.2f",
             tag, mode, k0, cap * 100, fx * 100 / 100)

    g = [f"[0:v]tpad=stop_mode=clone:stop_duration={extra}[src]"]
    if mode == "cover":
        g.append(f"[src]scale=w='trunc({sw * k0:.4f}*{Z}/2)*2':h='trunc({sh * k0:.4f}*{Z}/2)*2':"
                 f"eval=frame:flags=bicubic,"
                 f"crop={W}:{H}:x='clip({fx:.3f}*iw-{W}/2,0,iw-{W})':y='(ih-{H})/2',setsar=1[base]")
    else:
        g.append("[src]split[bga][fga]")
        g.append(f"[bga]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"boxblur=28:6,eq=brightness=-0.12[bg]")
        g.append(f"[fga]scale=w='trunc({W}*{Z}/2)*2':h=-2:eval=frame:flags=bicubic[fg]")
        g.append(f"[bg][fg]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame,setsar=1[base]")

    # entrées : 0 cut, 1 sfx, [2 musique], puis PNG
    inputs = ["-i", cut_path, "-i", sfx_path]
    nxt = 2
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        nxt = 3
    items = []
    for (png, t0, dur, x, y) in pngs:
        inputs += ["-loop", "1", "-framerate", fps, "-t", f"{dur:.3f}", "-i", png]
        items.append((nxt, t0, dur, x, y))
        nxt += 1
    ol, cur = overlay_chain("base", items, fps)
    g += ol
    g.append(f"[{cur}]ass={ass_name},fade=t=out:st={total - 0.5:.3f}:d=0.5[vout]")

    # ---- audio : voix + SFX (+ musique avec ducking), loudnorm, limiteur
    g.append(f"[0:a]aresample=48000,apad=whole_dur={total:.3f}[voice]")
    g.append(f"[1:a]aresample=48000,volume=0.8,apad=whole_dur={total:.3f}[fx]")
    if music:
        g.append("[voice]asplit=2[vm][vs]")
        g.append(f"[2:a]aresample=48000,volume=0.45,atrim=0:{total:.3f}[mu]")
        g.append("[mu][vs]sidechaincompress=threshold=0.02:ratio=10:attack=20:release=450[md]")
        g.append("[vm][fx][md]amix=inputs=3:normalize=0:duration=first[mx]")
    else:
        g.append("[voice][fx]amix=inputs=2:normalize=0:duration=first[mx]")
    g.append(f"[mx]loudnorm=I={prof['loud']}:TP=-1.5:LRA=11,aresample=48000,"
             f"alimiter=limit=0.89,afade=t=out:st={total - 0.6:.3f}:d=0.6[aout]")

    gp = inter / f"graph_{tag}.txt"
    gp.write_text(";\n".join(g), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + inputs + [
        "-filter_complex_script", gp, "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}"]
    enc = common.encoder_args(gpu, crf)
    cmd += enc + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                  "-movflags", "+faststart", out]
    log.info("[%s] rendu final -> %s (%.1fs)", tag, out, total)
    try:
        run(cmd, cwd=inter)  # cwd = intermediaires : le .ass est référencé en relatif
    except MontageError:
        if enc[1] != "libx264":
            log.warning("Encodeur matériel en échec -> nouvel essai en logiciel")
            common._ENC_CACHE.clear()
            cmd = [c for c in cmd]
            i = cmd.index("-c:v")
            cmd[i:i + len(enc)] = common.encoder_args(False, crf)
            run(cmd, cwd=inter)
        else:
            raise
    return out

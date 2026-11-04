#!/usr/bin/env python3
"""Rendu image par image du spot vertical 1080x1920 @30 i/s.

Chaque plan est une fonction du temps absolu t -> image RGBA. Les mouvements de caméra
(zoom lent, travelling, panoramique, « pull-back ») sont des recadrages sub-pixel dans
des sources suréchantillonnées ; les visages et la tenue du formateur ne sont jamais
retouchés, seulement cadrés. Transitions, textes, maquettes de smartphone et de timeline
sont dessinés ici. Les images sont envoyées brutes à FFmpeg (H.264).
"""
import math
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import plan
from plan import FPS, H, W, word_time

P = plan.load()
T_TOTAL = P["total"]
SC = {s["key"]: s for s in P["scenes"]}
LN = P["lines"]

WHITE = (255, 255, 255)
ORANGE = (255, 122, 38)
YELLOW = (255, 206, 46)
NAVY = (7, 12, 34)
RED = (235, 45, 58)
BLUE = (70, 150, 255)
DARK = (14, 16, 24)

FONT_DIR = "/usr/share/fonts/opentype/inter/"
FONTS = {"black": "InterDisplay-Black.otf", "xbold": "InterDisplay-ExtraBold.otf",
         "bold": "Inter-Bold.otf", "semi": "Inter-SemiBold.otf", "med": "Inter-Medium.otf"}


# =========================================================================== utilitaires
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def e_out(p):
    return 1 - (1 - p) ** 3


def e_inout(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def e_back(p, s=1.9):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def lerp(a, b, p):
    return a + (b - a) * p


@lru_cache(None)
def font(w, size):
    return ImageFont.truetype(FONT_DIR + FONTS[w], size)


def comp(canvas, im, x, y):
    """alpha_composite tolérant aux débordements."""
    x, y = int(round(x)), int(round(y))
    cw, ch = canvas.size
    iw, ih = im.size
    l, t = max(0, -x), max(0, -y)
    r, b = min(iw, cw - x), min(ih, ch - y)
    if r <= l or b <= t:
        return
    if (l, t, r, b) != (0, 0, iw, ih):
        im = im.crop((l, t, r, b))
    canvas.alpha_composite(im, (x + l, y + t))


def fade(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


def put(canvas, im, cx, cy, alpha=1.0, scale=1.0, rot=0.0):
    """Pose `im` centré en (cx, cy) avec opacité, échelle et rotation."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.004:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    comp(canvas, fade(im, alpha), cx - im.width / 2, cy - im.height / 2)


def rrect(size, radius, fill, ss=3, outline=None, width=0):
    """Rectangle arrondi anti-crénelé (suréchantillonnage)."""
    w, h = size
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius * ss, fill=fill,
                        outline=outline, width=width * ss)
    return im.resize((w, h), Image.LANCZOS)


def shadowed(im, blur=18, off=(0, 12), alpha=150, spread=None):
    pad = blur * 3
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", im.size, (0, 0, 0, 255))
    blk.putalpha(a)
    sh.paste(blk, (pad + off[0], pad + off[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(im, (pad, pad))
    return out


@lru_cache(None)
def text(s, size, color=WHITE, weight="black", glow=None, shadow=True, stroke=0,
         stroke_col=(0, 0, 0), track=0):
    """Texte pré-rendu en RGBA (ombre portée, halo lumineux optionnel)."""
    f = font(weight, size)
    if track:
        widths = [f.getlength(c) + track for c in s]
        tw = int(sum(widths) - track)
    else:
        tw = int(f.getlength(s))
    asc, desc = f.getmetrics()
    th = asc + desc
    pad = int(size * 0.45) + stroke
    im = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))

    def draw_txt(d, fill, ox=0, oy=0, sw=0, sf=None):
        if track:
            x = pad + ox
            for c, wdt in zip(s, widths):
                d.text((x, pad + oy), c, font=f, fill=fill, stroke_width=sw, stroke_fill=sf)
                x += wdt
        else:
            d.text((pad + ox, pad + oy), s, font=f, fill=fill, stroke_width=sw, stroke_fill=sf)

    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw_txt(ImageDraw.Draw(sh), (0, 0, 0, 170), 0, int(size * 0.05), stroke, (0, 0, 0, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size * 0.07)))
    if glow:
        gl = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw_txt(ImageDraw.Draw(gl), glow + (255,), sw=max(2, size // 25), sf=glow + (255,))
        gl = gl.filter(ImageFilter.GaussianBlur(size * 0.22))
        im.alpha_composite(gl)
        im.alpha_composite(fade(gl, 0.6))
    draw_txt(ImageDraw.Draw(im), color + (255,) if len(color) == 3 else color, sw=stroke,
             sf=stroke_col)
    return im


@lru_cache(None)
def pill_text(s, size, fg, bg, weight="black", padx=None, pady=None, radius=None, track=0):
    t = text(s, size, fg, weight, shadow=False, track=track)
    f = font(weight, size)
    padx = padx if padx is not None else int(size * 0.55)
    pady = pady if pady is not None else int(size * 0.28)
    tw = int(f.getlength(s) + (len(s) - 1) * track)
    asc, desc = f.getmetrics()
    capH = int(size * 0.74)
    w, h = tw + 2 * padx, capH + 2 * pady
    box = rrect((w, h), radius if radius is not None else h // 2, bg + (255,))
    pad = int(size * 0.45)
    # centrage vertical sur la hauteur des capitales
    ty = pady - pad - (asc - capH) + int(size * 0.02)
    box.alpha_composite(t, (padx - pad, ty)) if ty >= 0 and padx >= pad else comp(box, t, padx - pad, ty)
    return shadowed(box, 14, (0, 8), 140)


@lru_cache(None)
def sparkle(size, color=ORANGE, rays=12, glow=True):
    """Étoile éclatée générique (icône « IA »), dessinée en vectoriel."""
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    rnd = np.random.default_rng(3)
    for i in range(rays):
        a = 2 * math.pi * i / rays + 0.12
        r0, r1 = S * 0.07, S * (0.40 + 0.08 * rnd.random())
        wdt = S * 0.075
        x0, y0 = c + r0 * math.cos(a), c + r0 * math.sin(a)
        x1, y1 = c + r1 * math.cos(a), c + r1 * math.sin(a)
        d.line((x0, y0, x1, y1), fill=color + (255,), width=int(wdt))
        for (x, y) in ((x0, y0), (x1, y1)):
            d.ellipse((x - wdt / 2, y - wdt / 2, x + wdt / 2, y + wdt / 2), fill=color + (255,))
    im = im.resize((size, size), Image.LANCZOS)
    if glow:
        pad = size // 2
        out = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
        g = Image.new("RGBA", out.size, (0, 0, 0, 0))
        g.paste(im, (pad, pad))
        out.alpha_composite(g.filter(ImageFilter.GaussianBlur(size * 0.12)))
        out.alpha_composite(im, (pad, pad))
        return out
    return im


@lru_cache(None)
def radial(size, color, alpha=255, power=2.0):
    y, x = np.mgrid[0:size, 0:size]
    r = np.sqrt((x - size / 2) ** 2 + (y - size / 2) ** 2) / (size / 2)
    a = (np.clip(1 - r, 0, 1) ** power * alpha).astype(np.uint8)
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")


@lru_cache(None)
def vgrad(h, a0, a1, color=(0, 0, 0)):
    a = np.linspace(a0, a1, h).astype(np.uint8)
    arr = np.zeros((h, W, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a[:, None]
    return Image.fromarray(arr, "RGBA")


# =========================================================================== sources
UP = 2.3   # facteur de suréchantillonnage des photos


def _grade(im):
    im = ImageEnhance.Contrast(im).enhance(1.07)
    im = ImageEnhance.Color(im).enhance(1.06)
    a = np.asarray(im).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True)
    # étalonnage léger : ombres froides, hautes lumières chaudes (peaux préservées)
    a = a + (0.5 - lum) * np.array([-0.012, 0.0, 0.03]) * 0.8 + (lum - 0.5) * np.array([0.02, 0.006, -0.02])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def _load_sources():
    src, blur = {}, {}
    for i in (1, 2, 3):
        im = _grade(Image.open(plan.IMAGES / f"{i}.webp").convert("RGB"))
        big = im.resize((int(im.width * UP), int(im.height * UP)), Image.LANCZOS)
        big = big.filter(ImageFilter.UnsharpMask(2.2, 70, 2))
        src[i] = big
        # fond flou plein cadre (pour les plans « illustration »)
        crop = im.crop((im.width / 2 - 300, 0, im.width / 2 + 300, im.height)).resize((W, H), Image.BILINEAR)
        b = crop.filter(ImageFilter.GaussianBlur(38))
        b = ImageEnhance.Brightness(b).enhance(0.42)
        blur[i] = b.convert("RGBA")
    return src, blur


SRC, BLUR = _load_sources()
OW, OH = 1672, 941


def cam(i, cx, cy, z, size=(W, H)):
    """Recadrage caméra : centre (cx, cy) en pixels de l'image d'origine, zoom z
    (z=1 : toute la hauteur de la photo). Retourne une image RGB de `size`."""
    w, h = size
    s = (OH / z) / h * min(1.0, (OW / (OH / h * w)) if w / h > OW / OH else 1.0)
    hw, hh = w / 2 * s, h / 2 * s
    cx = clamp(cx, hw, OW - hw)
    cy = clamp(cy, hh, OH - hh)
    a = s * UP
    return SRC[i].transform(size, Image.AFFINE, (a, 0, (cx - hw) * UP, 0, a, (cy - hh) * UP),
                            resample=Image.BILINEAR)


def cam_move(i, t, t0, t1, k0, k1, ease=e_inout, size=(W, H)):
    p = ease(prog(t, t0, t1 - t0))
    return cam(i, *(lerp(a, b, p) for a, b in zip(k0, k1)), size=size)


# =========================================================================== éléments UI
SCREEN_PAD = 20


@lru_cache(None)
def phone_parts(w, h):
    r = int(w * 0.14)
    body = rrect((w, h), r, (18, 18, 22, 255), outline=(92, 94, 104, 255), width=3)
    inner = rrect((w - 2 * SCREEN_PAD, h - 2 * SCREEN_PAD), r - SCREEN_PAD, (255, 255, 255, 255))
    mask = inner.getchannel("A")
    island = rrect((int(w * 0.28), int(w * 0.075)), int(w * 0.04), (0, 0, 0, 255))
    shadow = shadowed(Image.new("RGBA", (w, h), (0, 0, 0, 0)), 1, (0, 0), 0)  # placeholder taille
    sh = Image.new("RGBA", (w + 160, h + 160), (0, 0, 0, 0))
    blk = rrect((w, h), r, (0, 0, 0, 200))
    sh.alpha_composite(blk, (80, 100))
    sh = sh.filter(ImageFilter.GaussianBlur(34))
    # reflet vitre
    gl = np.zeros((h - 2 * SCREEN_PAD, w - 2 * SCREEN_PAD, 4), np.uint8)
    yy, xx = np.mgrid[0:gl.shape[0], 0:gl.shape[1]]
    band = np.clip(1 - np.abs((xx * 0.9 + yy * 0.45) - gl.shape[1] * 0.55) / (w * 0.25), 0, 1)
    gl[..., :3] = 255
    gl[..., 3] = (band * 22).astype(np.uint8)
    glare = Image.fromarray(gl, "RGBA")
    del shadow
    return body, mask, island, sh, glare


def phone(screen, w, h):
    """Assemble un smartphone (avec ombre) autour d'une image d'écran RGB/RGBA."""
    body, mask, island, sh, glare = phone_parts(w, h)
    out = sh.copy()
    ph = body.copy()
    scr = screen.convert("RGBA").resize(mask.size, Image.BILINEAR) if screen.size != mask.size else screen.convert("RGBA")
    scr.putalpha(mask)
    ph.alpha_composite(scr, (SCREEN_PAD, SCREEN_PAD))
    ph.alpha_composite(glare, (SCREEN_PAD, SCREEN_PAD))
    ph.alpha_composite(island, ((w - island.width) // 2, SCREEN_PAD + int(w * 0.03)))
    out.alpha_composite(ph, (80, 80))
    return out


def icon(kind, size, col=WHITE):
    """Petites icônes vectorielles pour les puces (script, ciseaux, CC, note, effets…)."""
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = col + (255,)
    lw = int(S * 0.09)
    if kind == "script":
        d.rounded_rectangle((S * .2, S * .1, S * .8, S * .9), S * .08, outline=c, width=lw)
        for k, y in enumerate((.32, .5, .68)):
            d.line((S * .32, S * y, S * (.68 if k < 2 else .55), S * y), fill=c, width=lw)
    elif kind == "cut":
        for y in (.72,):
            d.ellipse((S * .12, S * (y - .14), S * .40, S * (y + .14)), outline=c, width=lw)
            d.ellipse((S * .60, S * (y - .14), S * .88, S * (y + .14)), outline=c, width=lw)
        d.line((S * .34, S * .6, S * .74, S * .1), fill=c, width=lw)
        d.line((S * .66, S * .6, S * .26, S * .1), fill=c, width=lw)
    elif kind == "cc":
        d.rounded_rectangle((S * .08, S * .2, S * .92, S * .8), S * .12, outline=c, width=lw)
        f = font("black", int(S * .34))
        d.text((S * .5, S * .52), "CC", font=f, fill=c, anchor="mm")
    elif kind == "music":
        d.line((S * .38, S * .72, S * .38, S * .14), fill=c, width=lw)
        d.line((S * .38, S * .14, S * .82, S * .06), fill=c, width=lw)
        d.line((S * .82, S * .06, S * .82, S * .62), fill=c, width=lw)
        d.ellipse((S * .12, S * .62, S * .42, S * .86), fill=c)
        d.ellipse((S * .56, S * .52, S * .86, S * .76), fill=c)
    elif kind == "fx":
        return sparkle(size, col, 8, glow=False)
    elif kind == "check":
        d.line((S * .2, S * .52, S * .42, S * .74), fill=c, width=int(lw * 1.4))
        d.line((S * .42, S * .74, S * .82, S * .28), fill=c, width=int(lw * 1.4))
    elif kind == "heart":
        d.ellipse((S * .08, S * .14, S * .52, S * .58), fill=c)
        d.ellipse((S * .48, S * .14, S * .92, S * .58), fill=c)
        d.polygon([(S * .1, S * .44), (S * .9, S * .44), (S * .5, S * .9)], fill=c)
    elif kind == "play":
        d.polygon([(S * .25, S * .15), (S * .25, S * .85), (S * .85, S * .5)], fill=c)
    elif kind == "arrow":
        d.line((S * .12, S * .5, S * .8, S * .5), fill=c, width=int(lw * 1.3))
        d.line((S * .52, S * .2, S * .84, S * .5), fill=c, width=int(lw * 1.3))
        d.line((S * .52, S * .8, S * .84, S * .5), fill=c, width=int(lw * 1.3))
    return im.resize((size, size), Image.LANCZOS)


@lru_cache(None)
def chip(label, kind, accent):
    """Puce « fonction » : pastille d'icône colorée + libellé, sur verre sombre."""
    f = font("black", 46)
    tw = int(f.getlength(label))
    h = 96
    w = tw + h + 52
    im = rrect((w, h), h // 2, (16, 20, 38, 235), outline=accent + (255,), width=3)
    dot = rrect((h - 16, h - 16), (h - 16) // 2, accent + (255,))
    im.alpha_composite(dot, (8, 8))
    ic = icon(kind, 46)
    im.alpha_composite(ic, (8 + (h - 16 - 46) // 2, 8 + (h - 16 - 46) // 2))
    t = text(label, 46, WHITE, "black", shadow=False)
    pad = int(46 * 0.45)
    comp(im, t, h + 14 - pad, (h - 46 * 1.22) / 2 - pad)
    return shadowed(im, 16, (0, 10), 170)


# ----------------------------------------------------------------------- écran d'éditeur
def _thumb(i, cx, cy, z, w, h):
    return cam(i, cx, cy, z, size=(w, h))


@lru_cache(None)
def timeline_strip(width=1700, scale=1.0):
    """Bande de timeline (pistes vidéo / texte / musique / voix) pré-rendue."""
    th = 62
    hgt = 248
    im = Image.new("RGBA", (width, hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fsm = font("semi", 15)
    for x in range(0, width, 30):               # règle
        big = (x // 30) % 5 == 0
        d.line((x, 0, x, 12 if big else 6), fill=(150, 160, 190, 255), width=2)
        if big:
            d.text((x + 4, 0), f"0:{(x // 30) // 5 * 2:02d}", font=fsm, fill=(150, 160, 190, 255))
    shots = [(3, 640, 300, 2.2), (1, 900, 200, 2.0), (1, 1110, 400, 2.4), (2, 760, 400, 1.2),
             (3, 1050, 560, 2.0), (2, 640, 320, 2.6), (1, 900, 330, 1.8), (3, 640, 260, 2.6),
             (2, 1000, 260, 1.6), (1, 1000, 420, 1.5)]
    x, k = 6, 0
    while x < width:                           # piste vidéo : clips de vignettes
        n = 2 + k % 3
        clip_w = n * 74
        clip = Image.new("RGBA", (clip_w, th), (0, 0, 0, 255))
        for j in range(n):
            i, cx, cy, z = shots[(k + j) % len(shots)]
            clip.paste(_thumb(i, cx, cy, z, 74, th), (j * 74, 0))
        m = rrect((clip_w, th), 10, (255, 255, 255, 255)).getchannel("A")
        clip.putalpha(m)
        im.alpha_composite(clip, (x, 26))
        d.rounded_rectangle((x, 26, x + clip_w - 1, 26 + th - 1), 10, outline=(255, 255, 255, 200), width=2)
        x += clip_w + 6
        k += 1
    labels = [("Titre", (138, 92, 246)), ("Sous-titres", (59, 130, 246)), ("Zoom", (236, 72, 153)),
              ("Transition", (20, 184, 166)), ("Sous-titres", (59, 130, 246)), ("CTA", ORANGE)]
    x, k = 20, 0
    while x < width:                           # piste texte / effets
        lab, col = labels[k % len(labels)]
        w_ = int(fsm.getlength(lab)) + 36 + (k % 2) * 60
        d.rounded_rectangle((x, 100, x + w_, 134), 9, fill=col + (255,))
        d.text((x + 14, 117), lab, font=font("bold", 17), fill=WHITE + (255,), anchor="lm")
        x += w_ + 26 + (k % 3) * 18
        k += 1
    rnd = np.random.default_rng(11)
    for row, (y0, col, amp) in enumerate(((150, (34, 197, 94), 36), (200, (56, 189, 248), 30))):
        d.rounded_rectangle((4, y0, width - 4, y0 + 42), 10, fill=col + (60,))
        env = 0.5 + 0.5 * np.sin(np.arange(width) / (37 + row * 23)) ** 2
        for x in range(10, width - 10, 5):
            a = amp * (0.25 + 0.75 * rnd.random() * env[x]) / 2
            if row == 1 and (x // 140) % 3 == 2:
                a = 2
            d.line((x, y0 + 21 - a, x, y0 + 21 + a), fill=col + (255,), width=3)
    return im


def editor_screen(t, t0, w, h, cues):
    """Écran d'application de montage (aperçu animé + timeline qui défile)."""
    scr = Image.new("RGBA", (w, h), (11, 13, 22, 255))
    d = ImageDraw.Draw(scr)
    lt = t - t0
    # barre d'état + barre de projet
    d.text((34, 44), "9:41", font=font("bold", 20), fill=WHITE)
    d.rounded_rectangle((w - 72, 38, w - 36, 54), 4, outline=WHITE, width=2)
    d.rectangle((w - 69, 41, w - 46, 51), fill=WHITE)
    d.text((24, 98), "‹", font=font("bold", 40), fill=WHITE, anchor="lm")
    d.text((w / 2, 98), "Promo_Formation", font=font("bold", 21), fill=WHITE, anchor="mm")
    exp = pill_text("Exporter", 18, WHITE, ORANGE, "bold")
    comp(scr, exp, w - exp.width + 4, 98 - exp.height / 2 - 2)
    # aperçu 9:16
    pw, ph_ = 300, 534
    px, py = (w - pw) // 2, 130
    prev = cam(3, lerp(640, 640, 0), lerp(300, 260, prog(lt, 0, 7)), lerp(1.6, 1.9, prog(lt, 0, 7)), size=(pw, ph_)).convert("RGBA")
    pd = ImageDraw.Draw(prev)
    if t >= cues.get("subs", 1e9):           # sous-titres incrustés dans l'aperçu
        a = prog(t, cues["subs"], 0.2)
        cap = text("TU VAS ADORER", 26, YELLOW, "black", stroke=3)
        comp(prev, fade(cap, a), (pw - cap.width) / 2, ph_ * 0.70 - cap.height / 2)
    if t >= cues.get("fx", 1e9):             # éclat « effets »
        p = prog(t, cues["fx"], 0.6)
        sp = sparkle(90, YELLOW)
        put(prev, sp, pw * 0.78, ph_ * 0.2, (1 - p) * 1.0, 0.6 + p * 0.8, p * 90)
        prev = Image.blend(prev, Image.new("RGBA", prev.size, (255, 255, 255, 255)), 0.35 * (1 - p))
    m = rrect((pw, ph_), 18, (255, 255, 255, 255)).getchannel("A")
    prev.putalpha(m)
    scr.alpha_composite(prev, (px, py))
    # transport
    ty = py + ph_ + 34
    comp(scr, icon("play", 30), w / 2 - 15, ty - 15)
    sec = 12 + lt * 1.0
    d.text((30, ty), f"00:{int(sec):02d}", font=font("semi", 19), fill=(200, 205, 225), anchor="lm")
    d.text((w - 30, ty), "00:45", font=font("semi", 19), fill=(120, 128, 150), anchor="rm")
    # timeline défilante, tête de lecture fixe au centre
    strip = timeline_strip()
    tl_y = ty + 30
    off = int(120 + lt * 95)
    if t >= cues.get("cut", 1e9):            # léger « saut » au moment de la coupe
        off += int(30 * e_out(prog(t, cues["cut"], 0.3)))
    crop = strip.crop((off, 0, off + w, strip.height))
    if t >= cues.get("music", 1e9):          # piste musique mise en avant
        a = 0.5 + 0.5 * math.sin((t - cues["music"]) * 9)
        hl = Image.new("RGBA", (w, 46), (34, 197, 94, int(60 * a)))
        crop.alpha_composite(hl, (0, 148))
    scr.alpha_composite(crop, (0, tl_y))
    d.line((w / 2, tl_y - 6, w / 2, tl_y + strip.height + 4), fill=YELLOW, width=4)
    d.polygon([(w / 2 - 10, tl_y - 14), (w / 2 + 10, tl_y - 14), (w / 2, tl_y - 2)], fill=YELLOW)
    if t >= cues.get("cut", 1e9):            # ciseaux sur la tête de lecture
        p = prog(t, cues["cut"], 0.7)
        ic = icon("cut", 44, YELLOW)
        put(scr, ic, w / 2, tl_y + 58, (1 - p) ** 0.5, 1 + 0.4 * p)
    # barre d'outils
    by = h - 70
    tools = [("cut", "Couper"), ("cc", "Texte"), ("music", "Audio"), ("fx", "Effets"), ("script", "IA")]
    for k, (kind, lab) in enumerate(tools):
        x = (k + 0.5) * w / len(tools)
        col = ORANGE if lab == "IA" else WHITE
        comp(scr, icon(kind, 34, col), x - 17, by - 30)
        d.text((x, by + 22), lab, font=font("semi", 16), fill=col, anchor="mm")
    return scr


# =========================================================================== plans
def bottom_shade(c, y0=900, a1=225):
    comp(c, vgrad(H - y0, 0, a1), 0, y0)


def top_shade(c, h=420, a0=150):
    comp(c, vgrad(h, a0, 0), 0, 0)


def word_pop(c, im, cx, cy, t0, t, dy=60, dur=0.32, back=True):
    p = prog(t, t0, dur)
    if p <= 0:
        return
    s = (0.82 + 0.18 * e_back(p)) if back else 1
    put(c, im, cx, cy + dy * (1 - e_out(p)), min(1, p * 1.6), s)


def scene_intro(t):
    c = BLUR[2].copy()
    z = 1.04 + 0.05 * t
    c = c.resize((int(W * z), int(H * z)), Image.BILINEAR).crop(
        (int(W * (z - 1) / 2), int(H * (z - 1) / 2), int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H))
    c = ImageEnhance.Brightness(c).enhance(0.6)
    p = e_back(prog(t, 0.05, 0.55), 1.4)
    put(c, radial(900, ORANGE, 120, 2.2), W / 2, H / 2 - 80, prog(t, 0, 0.6))
    put(c, sparkle(300), W / 2, H / 2 - 120, min(1, p * 1.5), 0.3 + 0.7 * p, -120 * (1 - p) + 20 * t)
    tt = text("NOUVELLE FORMATION", 44, WHITE, "xbold", track=14)
    put(c, tt, W / 2, H / 2 + 110, prog(t, 0.3, 0.3), 1, 0)
    # trait de lumière qui traverse
    lx = lerp(-300, W + 300, e_inout(prog(t, 0.2, 0.7)))
    put(c, streak(), lx, H / 2 + 160, 0.9)
    return c


@lru_cache(None)
def streak():
    arr = np.zeros((40, 900, 4), np.uint8)
    x = np.linspace(-1, 1, 900)
    y = np.linspace(-1, 1, 40)
    a = np.exp(-(x[None, :] ** 2) * 3) * np.exp(-(y[:, None] ** 2) * 18)
    arr[..., 0], arr[..., 1], arr[..., 2] = 255, 200, 140
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def viewfinder(c, t, t0):
    """Habillage « caméra » : coins de cadre, REC clignotant, time-code."""
    a = prog(t, t0, 0.3)
    if a <= 0:
        return
    d = ImageDraw.Draw(c)
    col = (255, 255, 255, int(200 * a))
    m, L = 70, 80
    y0, y1 = 210, 1500
    for (x, y, sx, sy) in ((m, y0, 1, 1), (W - m, y0, -1, 1), (m, y1, 1, -1), (W - m, y1, -1, -1)):
        d.line((x, y, x + sx * L, y), fill=col, width=6)
        d.line((x, y, x, y + sy * L), fill=col, width=6)
    if int(t * 2.2) % 2 == 0:
        d.ellipse((m + 20, y0 + 30, m + 50, y0 + 60), fill=(235, 45, 58, int(255 * a)))
    d.text((m + 64, y0 + 45), "REC", font=font("black", 34), fill=col, anchor="lm")
    fr = int((t - t0) * 30)
    d.text((W - m - 20, y0 + 45), f"00:00:{fr // 30:02d}:{fr % 30:02d}", font=font("semi", 30),
           fill=col, anchor="rm")


def scene_hook(t):
    s = SC["hook"]
    c = cam_move(3, t, s["start"] - 0.3, s["end"] + 0.3, (630, 520, 1.0), (625, 330, 1.22)).convert("RGBA")
    bottom_shade(c, 820, 235)
    top_shade(c, 380, 120)
    viewfinder(c, t, s["start"])
    word_pop(c, text("ET SI TON", 92, WHITE), W / 2, 1110, word_time("hook", "Et") - 0.05, t)
    word_pop(c, text("TÉLÉPHONE", 150, ORANGE, glow=(255, 90, 0)), W / 2, 1255,
             word_time("hook", "téléphone") - 0.08, t, dy=0)
    word_pop(c, text("DEVENAIT UN VRAI", 76, WHITE), W / 2, 1395, word_time("hook", "devenait") - 0.05, t)
    p = prog(t, word_time("hook", "studio") - 0.08, 0.35)
    if p > 0:
        box = pill_text("STUDIO DE MONTAGE ?", 70, DARK, YELLOW, "black", radius=18)
        put(c, box, W / 2, 1515, min(1, p * 2), 0.6 + 0.4 * e_back(p), -3 * (1 - e_out(p)))
    return c


def scene_claude(t):
    s = SC["claude"]
    c = cam_move(1, t, s["start"] - 0.3, s["end"] + 0.3, (905, 430, 1.06), (1010, 400, 1.32)).convert("RGBA")
    bottom_shade(c, 850, 235)
    tc = word_time("claude", "Claude")
    # lueur orange qui « s'allume » sur le mot clé
    gp = prog(t, tc - 0.1, 0.5)
    if gp > 0:
        put(c, radial(1100, ORANGE, 90, 1.6), W / 2, 1140, gp * (0.8 + 0.2 * math.sin(t * 5)))
    word_pop(c, text("AVEC", 70, WHITE, "xbold", track=8), W / 2, 1000, word_time("claude", "Avec") - 0.05, t)
    p = prog(t, tc - 0.08, 0.4)
    if p > 0:
        title = text("CLAUDE AI", 140, ORANGE, glow=(255, 100, 10))
        sc = 1.25 - 0.25 * e_out(p)
        put(c, title, W / 2 + 55, 1130, min(1, p * 2.5), sc)
        sp = sparkle(150)
        put(c, sp, W / 2 + 55 - (title.width - 126) * sc / 2 - 70, 1130, min(1, p * 2), (0.4 + 0.6 * e_back(p)),
            -90 * (1 - p) - 25 * (t - tc))
    # carte « assistant de réalisation » (frappe progressive)
    ti = word_time("claude", "intelligence") - 0.1
    p = prog(t, ti, 0.45)
    if p > 0:
        card = assistant_card(t, ti)
        put(c, card, W / 2, 1400 + 140 * (1 - e_out(p)), min(1, p * 2))
    return c


ASSIST_TXT = "Accroche 3 s · plans serrés · sous-titres · musique · appel à l'action ✓"


def assistant_card(t, t0):
    w, h = 920, 250
    card = rrect((w, h), 34, (250, 248, 244, 246))
    d = ImageDraw.Draw(card)
    comp(card, sparkle(74, ORANGE, glow=False), 30, 26)
    d.text((124, 62), "Assistant de réalisation", font=font("black", 40), fill=DARK, anchor="lm")
    dots = "•" * (1 + int(t * 4) % 3)
    d.text((w - 34, 62), "IA", font=font("black", 30), fill=ORANGE, anchor="rm")
    n = int(len(ASSIST_TXT) * prog(t, t0 + 0.35, 2.6))
    shown = ASSIST_TXT[:n].replace("✓", "")
    f = font("semi", 33)
    # retour à la ligne simple
    lines, cur = [], ""
    for wd in shown.split(" "):
        tst = (cur + " " + wd).strip()
        if f.getlength(tst) > w - 80:
            lines.append(cur)
            cur = wd
        else:
            cur = tst
    lines.append(cur)
    for k, ln in enumerate(lines[:3]):
        d.text((40, 128 + k * 46), ln, font=f, fill=(55, 58, 70))
    if n < len(ASSIST_TXT):
        lx = 40 + f.getlength(lines[min(2, len(lines) - 1)]) + 6
        ly = 128 + (min(2, len(lines) - 1)) * 46
        if int(t * 3) % 2 == 0:
            d.rectangle((lx, ly + 4, lx + 4, ly + 38), fill=ORANGE)
    else:
        ck = rrect((44, 44), 22, (34, 197, 94, 255))
        ck.alpha_composite(icon("check", 44))
        comp(card, ck, w - 80, h - 72)
    del dots
    return shadowed(card, 24, (0, 16), 160)


@lru_cache(None)
def beams():
    """Faisceaux de projecteurs (habillage des plans « illustration »)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for k, (x, ang, col) in enumerate(((180, 14, BLUE), (540, 0, (140, 170, 255)), (900, -14, BLUE))):
        b = Image.new("RGBA", (420, 2200), (0, 0, 0, 0))
        dd = ImageDraw.Draw(b)
        dd.polygon([(190, 0), (230, 0), (420, 2200), (0, 2200)], fill=col + (38,))
        b = b.filter(ImageFilter.GaussianBlur(30)).rotate(ang, Image.BICUBIC, expand=True)
        comp(im, b, x - b.width / 2, -150)
    return im


def stage_bg(i, t, tint=(20, 40, 110)):
    c = BLUR[i].copy()
    ov = Image.new("RGBA", (W, H), tint + (90,))
    c.alpha_composite(ov)
    sh = int(40 * math.sin(t * 0.7))
    comp(c, beams(), sh, 0)
    put(c, radial(1400, (40, 90, 255), 70, 1.8), W / 2, H * 0.45, 1)
    return c


CHIPS = [("SCRIPT", "script", (138, 92, 246), "Script", 250, 560, -1),
         ("DÉCOUPAGE", "cut", (236, 72, 153), "découpage", 820, 730, 1),
         ("SOUS-TITRES", "cc", (59, 130, 246), "sous-titres", 270, 900, -1),
         ("MUSIQUE", "music", (34, 197, 94), "musique", 830, 1070, 1),
         ("EFFETS", "fx", ORANGE, "effets", 250, 1240, -1)]


def scene_montage(t):
    s = SC["montage"]
    t0 = s["start"]
    c = stage_bg(2, t)
    # titre
    p = prog(t, t0 + 0.05, 0.4)
    put(c, text("MONTAGE VIDÉO", 108, WHITE, glow=(60, 120, 255)), W / 2, 250 + 40 * (1 - e_out(p)), p)
    bar_w = int(560 * e_out(prog(t, t0 + 0.3, 0.5)))
    if bar_w > 4:
        comp(c, rrect((bar_w, 12), 6, ORANGE + (255,)), W / 2 - bar_w / 2, 335)
    # smartphone : entrée par le bas + flottement
    pe = e_out(prog(t, t0 - 0.1, 0.65))
    cues = {"cut": word_time("montage", "découpage"), "subs": word_time("montage", "sous-titres"),
            "music": word_time("montage", "musique"), "fx": word_time("montage", "effets")}
    scr = editor_screen(t, t0, 540 - 2 * SCREEN_PAD, 1100 - 2 * SCREEN_PAD, cues)
    ph = phone(scr, 540, 1100)
    rot = lerp(8, 0, pe) + 1.2 * math.sin((t - t0) * 1.3)
    put(c, ph, W / 2 + 20 * (1 - pe), 940 + 900 * (1 - pe), 1, 1, rot)
    # puces synchronisées sur chaque mot
    for label, kind, col, needle, x, y, side in CHIPS:
        tw = word_time("montage", needle) - 0.06
        p = prog(t, tw, 0.35)
        if p > 0:
            ch = chip(label, kind, col)
            fl = 6 * math.sin((t - tw) * 2.2 + x)
            put(c, ch, x + side * 120 * (1 - e_out(p)), y + fl, min(1, p * 2.2), 0.6 + 0.4 * e_back(p))
    # « DE A À Z »
    tz = word_time("montage", "de", occurrence=0)
    # (le premier « de » de la réplique est celui de « de A à Z »)
    p = prog(t, tz - 0.05, 0.35)
    if p > 0:
        put(c, pill_text("DE A À Z", 84, DARK, YELLOW, radius=20), W / 2, 1560, min(1, p * 2),
            0.5 + 0.5 * e_back(p), 4 * (1 - p))
    else:
        captions(c, t, "montage", word_time("montage", "tu") - 0.05, tz - 0.05, 1560)
    return c


def captions(c, t, key, ta, tb, y):
    """Sous-titres mot à mot (mot prononcé en jaune) entre ta et tb."""
    if not (ta <= t < tb):
        return
    words = [w for w in LN[key]["words"] if ta - 0.01 <= w["t0"] < tb]
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or len(" ".join(x["w"] for x in cur)) > 18:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0]["t0"] if gi + 1 < len(groups) else tb
        if g[0]["t0"] - 0.08 <= t < g_end:
            ims = []
            for w in g:
                active = w["t0"] <= t
                ims.append(text(w["w"].upper().strip(",.…"), 66, YELLOW if active else WHITE, "black",
                                stroke=5, shadow=True))
            pad = int(66 * 0.45) + 5
            widths = [im.width - 2 * pad for im in ims]
            gap = 22
            tot = sum(widths) + gap * (len(ims) - 1)
            x = W / 2 - tot / 2
            pg = prog(t, g[0]["t0"] - 0.08, 0.15)
            for im, wd, w in zip(ims, widths, g):
                sc = 1.0 + 0.08 * (1 - prog(t, w["t0"], 0.15)) * (w["t0"] <= t)
                put(c, im, x + wd / 2, y + 16 * (1 - e_out(pg)), pg, sc)
                x += wd + gap
            return


def strike(c, cx, cy, width, p, col=RED):
    if p <= 0:
        return
    w = int(width * e_out(p))
    if w < 4:
        return
    bar = rrect((w, 16), 8, col + (255,))
    put(c, bar, cx - width / 2 + w / 2, cy, 1, 1, 4)


def scene_mobile(t):
    s = SC["mobile"]
    tc = word_time("mobile", "Cent") - 0.06
    shake = 0
    sp = prog(t, tc, 0.35)
    if 0 < sp < 1:
        shake = (1 - sp) * 14 * math.sin(t * 90)
    base = cam_move(3, t, s["start"] - 0.3, s["end"] + 0.3, (600, 470, 1.02), (760, 420, 1.12))
    c = base.convert("RGBA")
    if shake:
        c = c.transform(c.size, Image.AFFINE, (1, 0, shake, 0, 1, shake * 0.6), Image.BILINEAR)
    bottom_shade(c, 760, 235)
    # « SANS ORDINATEUR » / « SANS LOGICIEL COMPLIQUÉ », barrés, puis balayés par « 100 % »
    out = e_inout(prog(t, tc - 0.1, 0.3))
    a_old = 1 - out
    if a_old > 0:
        t1 = word_time("mobile", "Sans")
        t2 = word_time("mobile", "Sans", occurrence=1)
        im1 = text("SANS ORDINATEUR", 96, WHITE)
        im2 = text("SANS LOGICIEL COMPLIQUÉ", 76, WHITE)
        cc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        word_pop(cc, im1, W / 2, 1100, t1 - 0.05, t)
        strike(cc, W / 2, 1110, im1.width - 70, prog(t, word_time("mobile", "ordinateur", "t1") - 0.1, 0.25))
        word_pop(cc, im2, W / 2, 1240, t2 - 0.05, t)
        strike(cc, W / 2, 1250, im2.width - 60, prog(t, word_time("mobile", "compliqué", "t1") - 0.1, 0.25))
        put(c, cc, W / 2, H / 2 - 160 * out, a_old)
    if sp > 0:
        fl = Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - prog(t, tc, 0.25)))))
        c.alpha_composite(fl)
        put(c, radial(1200, YELLOW, 110, 1.7), W / 2, 1200, min(1, sp * 2))
        big = text("100 %", 300, YELLOW, glow=(255, 150, 0))
        put(c, big, W / 2, 1180, min(1, sp * 3), 1.7 - 0.7 * e_out(sp))
        tp = prog(t, word_time("mobile", "sur") - 0.1, 0.35)
        if tp > 0:
            put(c, pill_text("SUR TÉLÉPHONE", 92, WHITE, ORANGE, radius=24), W / 2, 1400,
                min(1, tp * 2), 0.6 + 0.4 * e_back(tp))
            ph_icon = phone(cam(3, 640, 300, 1.8, (150, 270)), 190, 360)
            put(c, ph_icon, W - 150, 760 + 10 * math.sin(t * 2), tp, 0.9, -12 + 3 * math.sin(t * 1.5))
    return c


def reel_screen(i, k0, k1, t, t0, w, h, likes0, caption):
    scr = cam_move(i, t, t0, t0 + 6, k0, k1, ease=lambda p: p, size=(w, h)).convert("RGBA")
    comp(scr, vgrad(h // 2, 0, 170).resize((w, h // 2)), 0, h // 2)
    d = ImageDraw.Draw(scr)
    lt = max(0, t - t0)
    likes = likes0 + int(lt * 37 * (1 + lt))
    x = w - 46
    for k, (kind, lab) in enumerate((("heart", f"{likes / 1000:.1f}k".replace(".", ",")), ("play", "Vues"))):
        y = h * 0.55 + k * 92
        comp(scr, icon(kind, 46, (255, 70, 90) if kind == "heart" else WHITE), x - 23, y - 23)
        d.text((x, y + 38), lab, font=font("bold", 18), fill=WHITE, anchor="mm")
    d.text((26, h - 92), "@formation.montage", font=font("bold", 22), fill=WHITE)
    d.text((26, h - 60), caption, font=font("semi", 20), fill=(230, 230, 235))
    pr = (lt / 6) % 1
    d.rectangle((0, h - 8, w, h), fill=(255, 255, 255, 70))
    d.rectangle((0, h - 8, int(w * pr), h), fill=WHITE)
    return scr


@lru_cache(None)
def heart_sprite():
    return icon("heart", 70, (255, 70, 90))


def scene_publier(t):
    s = SC["publier"]
    t0 = s["start"]
    c = stage_bg(1, t, (90, 40, 20))
    put(c, radial(1300, ORANGE, 60, 1.6), W / 2, 820, 1)
    # titre
    p = prog(t, word_time("publier", "prêtes") - 0.1, 0.35)
    pt = prog(t, t0, 0.35)
    put(c, text("TES VIDÉOS", 84, WHITE, "xbold"), W / 2, 200 + 30 * (1 - e_out(pt)), pt)
    if p > 0:
        ttl = text("PRÊTES À PUBLIER", 112, YELLOW, glow=(255, 140, 0))
        put(c, ttl, W / 2, 315, min(1, p * 2), 0.7 + 0.3 * e_back(p))
    # trois téléphones en éventail
    specs = [(-1, 3, (640, 260, 1.9), (640, 300, 2.2), 2300, "Avant / après 🎬"),
             (1, 2, (900, 300, 1.4), (700, 320, 1.6), 5400, "Formation en direct"),
             (0, 1, (930, 300, 1.5), (1080, 380, 1.8), 12800, "Montage 100 % mobile")]
    for k, (side, i, k0, k1, likes, cap) in enumerate(specs):
        te = t0 - 0.05 + 0.12 * k
        pe = e_out(prog(t, te, 0.55))
        sw, sh_ = (500, 1000) if side == 0 else (420, 840)
        scr = reel_screen(i, k0, k1, t, t0, sw - 2 * SCREEN_PAD, sh_ - 2 * SCREEN_PAD, likes, cap.replace("🎬", ""))
        ph = phone(scr, sw, sh_)
        x = W / 2 + side * 300 + side * 500 * (1 - pe)
        y = 900 + (0 if side == 0 else 60) + (600 * (1 - pe) if side == 0 else 0)
        rot = -side * 9 * pe + side * 0
        put(c, ph, x, y + 8 * math.sin(t * 1.6 + k), min(1, pe * 1.5), 1, rot)
    # cœurs qui montent
    rnd = np.random.default_rng(5)
    for k in range(10):
        st = t0 + 0.8 + k * 0.38
        lp = (t - st) / 2.0
        if 0 < lp < 1:
            x = W / 2 + 150 + rnd.uniform(-40, 60) + 40 * math.sin(lp * 6 + k)
            y = 1150 - lp * 650
            put(c, heart_sprite(), x, y, (1 - lp) * min(1, lp * 5), 0.5 + 0.5 * lp)
    # plateformes
    plats = [("TikTok", (255, 0, 80), "TikTok", 230), ("Reels", (225, 48, 108), "Reels", 540),
             ("WhatsApp", (37, 211, 102), "WhatsApp", 850)]
    for label, col, needle, x in plats:
        tw = word_time("publier", needle) - 0.06
        p = prog(t, tw, 0.32)
        if p > 0:
            put(c, plat_chip(label, col), x, 1520 + 50 * (1 - e_out(p)), min(1, p * 2), 0.6 + 0.4 * e_back(p))
    return c


@lru_cache(None)
def plat_chip(label, col):
    f = font("black", 44)
    tw = int(f.getlength(label))
    h = 92
    w = tw + 96
    im = rrect((w, h), h // 2, (255, 255, 255, 245))
    d = ImageDraw.Draw(im)
    d.ellipse((24, h / 2 - 13, 50, h / 2 + 13), fill=col)
    d.text((64, h / 2 + 1), label, font=f, fill=DARK, anchor="lm")
    return shadowed(im, 14, (0, 8), 150)


def scene_afrique(t):
    s = SC["afrique"]
    c = cam_move(2, t, s["start"] - 0.35, s["end"] + 0.3, (640, 330, 1.95), (820, 470, 1.0),
                 ease=lambda p: e_out(p) * 0.85 + p * 0.15).convert("RGBA")
    top_shade(c, 520, 150)
    bottom_shade(c, 1000, 200)
    tf = word_time("afrique", "formation") - 0.08
    word_pop(c, text("FORMATION", 128, WHITE), W / 2, 1180, tf, t)
    word_pop(c, text("PRATIQUE", 128, ORANGE, glow=(255, 100, 10)), W / 2, 1310,
             word_time("afrique", "pratique") - 0.08, t)
    p = prog(t, word_time("afrique", "direct") - 0.1, 0.3)
    if p > 0:
        put(c, live_badge(t), W / 2, 330, min(1, p * 2), 0.6 + 0.4 * e_back(p))
    p = prog(t, word_time("afrique", "créateurs") - 0.1, 0.35)
    if p > 0:
        put(c, pill_text("CRÉATEURS DE TOUTE L'AFRIQUE", 56, DARK, YELLOW, radius=16), W / 2,
            1470 + 30 * (1 - e_out(p)), min(1, p * 2))
    return c


def live_badge(t):
    f = font("black", 52)
    lab = "EN DIRECT"
    tw = int(f.getlength(lab))
    h = 100
    w = tw + 120
    im = rrect((w, h), 18, RED + (255,))
    d = ImageDraw.Draw(im)
    a = 255 if int(t * 2.5) % 2 == 0 else 110
    d.ellipse((30, h / 2 - 16, 62, h / 2 + 16), fill=(255, 255, 255, a))
    d.text((84, h / 2 + 2), lab, font=f, fill=WHITE, anchor="lm")
    return shadowed(im, 14, (0, 8), 150)


@lru_cache(None)
def bokeh_field():
    rnd = np.random.default_rng(21)
    return [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(10, 46), rnd.uniform(0.3, 1.0),
             rnd.uniform(-60, -20), rnd.choice([0, 1])) for _ in range(26)]


def scene_cta(t):
    s = SC["cta"]
    t0 = s["start"]
    lt = t - t0
    c = BLUR[2].copy()
    ov = Image.new("RGBA", (W, H), NAVY + (150,))
    c.alpha_composite(ov)
    put(c, radial(1500, ORANGE, 80 + int(20 * math.sin(t * 3)), 1.8), W / 2, 1150, 1)
    for x, y, r, a, v, k in bokeh_field():
        yy = (y + v * lt) % H
        put(c, radial(int(r * 2), (255, 190, 120) if k else (120, 160, 255), int(140 * a), 1.2), x, yy, 1)
    # carte portrait du formateur (cadrage visage + tenue)
    pc = e_out(prog(t, t0 - 0.05, 0.5))
    cw, chh = 760, 640
    por = cam_move(3, t, t0, s["end"], (620, 300, 1.45), (630, 270, 1.62), size=(cw, chh)).convert("RGBA")
    por.putalpha(rrect((cw, chh), 42, (255, 255, 255, 255)).getchannel("A"))
    frame = rrect((cw + 12, chh + 12), 48, (255, 255, 255, 255))
    frame.alpha_composite(por, (6, 6))
    put(c, shadowed(frame, 30, (0, 20), 190), W / 2, 520 + 120 * (1 - pc), pc, 0.9 + 0.1 * pc)
    # badge places limitées
    p = prog(t, word_time("cta", "places") - 0.1, 0.35)
    if p > 0:
        put(c, pill_text("PLACES LIMITÉES", 50, WHITE, RED, radius=14, track=2), 300, 845,
            min(1, p * 2), 0.6 + 0.4 * e_back(p), 4)
    # titre final, mot à mot
    tm = word_time("cta", "maîtrise") - 0.08
    word_pop(c, text("MAÎTRISE LE", 82, WHITE, "xbold"), W / 2, 975, tm, t)
    word_pop(c, text("MONTAGE VIDÉO", 112, WHITE), W / 2, 1090, word_time("cta", "montage") - 0.08, t)
    tcl = word_time("cta", "Claude") - 0.1
    p = prog(t, tcl, 0.4)
    if p > 0:
        ttl = text("AVEC CLAUDE AI", 100, ORANGE, glow=(255, 100, 10))
        put(c, ttl, W / 2 + 45, 1215, min(1, p * 2), 1.2 - 0.2 * e_out(p))
        put(c, sparkle(100), W / 2 + 45 - (ttl.width - 90) / 2 - 60, 1215, min(1, p * 2), e_back(p), 30 * lt)
    p = prog(t, LN["cta"]["end"] - 0.15, 0.35)
    if p > 0:
        put(c, pill_text("100 % SUR TÉLÉPHONE", 64, DARK, YELLOW, radius=16), W / 2, 1345,
            min(1, p * 2), 0.6 + 0.4 * e_back(p))
    # bouton d'inscription : apparition, pulsation, reflet, « tap »
    ti = word_time("cta", "Inscris") - 0.08
    p = prog(t, ti, 0.4)
    if p > 0:
        btn = cta_button()
        pulse = 1 + 0.035 * math.sin((t - ti) * 6.5) * prog(t, ti + 0.4, 0.3)
        bimg = btn.copy()
        sx = ((t - ti) * 0.8) % 1.6 - 0.3
        sheen = shine(btn.size, sx)
        bimg.alpha_composite(sheen)
        put(c, bimg, W / 2, 1490 + 60 * (1 - e_out(p)), min(1, p * 2), (0.6 + 0.4 * e_back(p)) * pulse)
        tp = (t - ti - 0.5) % 2.2
        if t - ti > 0.5 and tp < 0.7:
            rp = tp / 0.7
            ring = ripple(int(60 + 160 * rp))
            put(c, ring, W / 2 + 230, 1505, (1 - rp) * 0.9)
            put(c, finger(), W / 2 + 270, 1580 - 20 * math.sin(rp * math.pi), 1)
    p = prog(t, ti + 0.6, 0.4)
    if p > 0:
        put(c, text("Lien d'inscription en description  ·  Écris-nous", 34, (225, 228, 240), "semi"),
            W / 2, 1610, p)
    return c


@lru_cache(None)
def cta_button():
    w, h = 860, 150
    im = rrect((w, h), h // 2, ORANGE + (255,))
    g = np.zeros((h, w, 4), np.uint8)
    g[..., :3] = 255
    g[..., 3] = (np.linspace(70, 0, h)[:, None] * np.ones(w)).astype(np.uint8)
    gl = Image.fromarray(g, "RGBA")
    gl.putalpha(Image.fromarray(np.minimum(np.asarray(gl.getchannel("A")), np.asarray(im.getchannel("A")))))
    im.alpha_composite(gl)
    d = ImageDraw.Draw(im)
    d.text((w / 2 - 30, h / 2 + 2), "JE M'INSCRIS", font=font("black", 70), fill=WHITE, anchor="mm")
    comp(im, icon("arrow", 60), w - 140, h / 2 - 30)
    out = Image.new("RGBA", (w + 120, h + 120), (0, 0, 0, 0))
    glow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    glow.alpha_composite(rrect((w, h), h // 2, ORANGE + (200,)), (60, 60))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)))
    out.alpha_composite(im, (60, 60))
    return out


def shine(size, pos):
    w, h = size
    arr = np.zeros((h, w, 4), np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    band = np.clip(1 - np.abs(xx + yy * 0.5 - pos * w) / 60, 0, 1)
    arr[..., :3] = 255
    arr[..., 3] = (band * 110).astype(np.uint8)
    m = np.asarray(cta_button().getchannel("A")) > 200
    arr[..., 3] *= m
    return Image.fromarray(arr, "RGBA")


@lru_cache(None)
def ripple(r):
    s = r * 2 + 8
    im = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((8, 8, s * 2 - 8, s * 2 - 8), outline=(255, 255, 255, 230), width=10)
    return im.resize((s, s), Image.LANCZOS)


@lru_cache(None)
def finger():
    """Pictogramme de doigt / curseur de tap (forme simple)."""
    ss = 4
    S = 90 * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((S * .3, S * .02, S * .62, S * .34), fill=(255, 255, 255, 255))
    d.rounded_rectangle((S * .3, S * .18, S * .62, S * .7), S * .16, fill=(255, 255, 255, 255))
    d.rounded_rectangle((S * .18, S * .45, S * .88, S * .98), S * .2, fill=(255, 255, 255, 255))
    im = im.resize((90, 90), Image.LANCZOS)
    return shadowed(im, 8, (0, 4), 160)


SCENES = {"intro": scene_intro, "hook": scene_hook, "claude": scene_claude, "montage": scene_montage,
          "mobile": scene_mobile, "publier": scene_publier, "afrique": scene_afrique, "cta": scene_cta}


# =========================================================================== transitions
def np_img(im):
    return np.asarray(im.convert("RGB"), dtype=np.float32)


def motion_blur(arr, dx, dy, taps=9):
    if abs(dx) + abs(dy) < 1:
        return arr
    acc = np.zeros_like(arr)
    for k in range(taps):
        f = (k / (taps - 1) - 0.5)
        acc += np.roll(arr, (int(f * dy), int(f * dx)), axis=(0, 1))
    return acc / taps


def zoom_img(arr, z):
    if abs(z - 1) < 1e-3:
        return arr
    im = Image.fromarray(arr.astype(np.uint8))
    w, h = int(W * z), int(H * z)
    im = im.resize((w, h), Image.BILINEAR) if z > 1 else im
    if z > 1:
        l, t = (w - W) // 2, (h - H) // 2
        return np.asarray(im.crop((l, t, l + W, t + H)), dtype=np.float32)
    return arr


def radial_blur(arr, strength, taps=6):
    acc = np.zeros_like(arr)
    for k in range(taps):
        acc += zoom_img(arr, 1 + strength * k / taps)
    return acc / taps


@lru_cache(None)
def leak_layer():
    rnd = np.random.default_rng(9)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _ in range(5):
        col = [ORANGE, YELLOW, (255, 80, 60)][rnd.integers(3)]
        put(im, radial(int(rnd.uniform(700, 1400)), col, 230, 1.4), rnd.uniform(0, W), rnd.uniform(0, H), 1)
    return np_img(Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), im))


def transition(kind, A, B, p):
    """A, B : tableaux float32 HxWx3 ; p ∈ [0,1]."""
    if kind == "flash":
        if p < 0.5:
            q = p * 2
            return A * (1 - q) + 255 * q
        q = (p - 0.5) * 2
        return zoom_img(B, 1 + 0.12 * (1 - e_out(q))) * q + 255 * (1 - q)
    if kind in ("whip", "whip_up"):
        e = e_inout(p)
        horiz = kind == "whip"
        n = W if horiz else H
        off = int(e * n)
        out = np.empty_like(A)
        if horiz:
            out[:, : W - off] = A[:, off:]
            out[:, W - off:] = B[:, : off]
        else:
            out[: H - off] = A[off:]
            out[H - off:] = B[: off]
        s = math.sin(math.pi * p) * 160
        return motion_blur(out, s if horiz else 0, 0 if horiz else s, 11)
    if kind == "zoom":
        if p < 0.5:
            q = e_inout(p * 2)
            out = radial_blur(zoom_img(A, 1 + 0.5 * q), 0.25 * q)
        else:
            q = e_inout((p - 0.5) * 2)
            out = radial_blur(zoom_img(B, 1.4 - 0.4 * q), 0.25 * (1 - q))
        fl = 1 - abs(p - 0.5) * 2
        return out * (1 - 0.35 * fl) + 255 * 0.35 * fl
    if kind == "leak":
        q = e_inout(p)
        mix = A * (1 - q) + B * q
        k = math.sin(math.pi * p)
        return 255 - (255 - mix) * (255 - leak_layer() * k) / 255
    if kind == "glitch":
        src = A if p < 0.5 else B
        k = 1 - abs(p - 0.5) * 2
        out = src.copy()
        sh = int(40 * k)
        out[..., 0] = np.roll(src[..., 0], sh, axis=1)
        out[..., 2] = np.roll(src[..., 2], -sh, axis=1)
        rnd = np.random.default_rng(int(p * 1000))
        for _ in range(int(10 * k)):
            y = rnd.integers(0, H - 80)
            hh = rnd.integers(10, 80)
            out[y:y + hh] = np.roll(out[y:y + hh], rnd.integers(-120, 120), axis=1)
        return out * (1 - 0.3 * k) + 255 * 0.3 * k
    return B


# =========================================================================== post-traitement
def _post_assets():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 * 0.8 + ((y - H / 2) / (H / 2)) ** 2)
    vig = (1 - 0.38 * np.clip(r - 0.45, 0, 1) ** 1.5)[..., None].astype(np.float32)
    rnd = np.random.default_rng(1)
    grain = [rnd.normal(0, 5.0, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
             for _ in range(6)]
    return vig, grain


VIG, GRAIN = _post_assets()


def scene_at(t):
    for s in P["scenes"]:
        if s["start"] <= t < s["end"]:
            return s
    return P["scenes"][-1]


def frame(n):
    t = n / FPS
    s = scene_at(t)
    idx = P["scenes"].index(s)
    arr = None
    half = plan.TRANS / 2
    nxt = P["scenes"][idx + 1] if idx + 1 < len(P["scenes"]) else None
    if nxt and t >= nxt["start"] - half:
        A, B, p, kind = s, nxt, (t - (nxt["start"] - half)) / plan.TRANS, plan.TRANSITIONS[nxt["key"]]
    elif idx > 0 and t < s["start"] + half:
        A, B, p, kind = P["scenes"][idx - 1], s, (t - (s["start"] - half)) / plan.TRANS, plan.TRANSITIONS[s["key"]]
    else:
        A = None
    if A is not None:
        arr = transition(kind, np_img(SCENES[A["key"]](t)), np_img(SCENES[B["key"]](t)), clamp(p))
    else:
        arr = np_img(SCENES[s["key"]](t))
    arr = arr * VIG + GRAIN[n % len(GRAIN)]
    # fondu au noir final
    fo = prog(t, T_TOTAL - 0.45, 0.45)
    if fo > 0:
        arr *= 1 - fo
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else str(plan.BUILD / "video.mp4")
    only = sys.argv[2] if len(sys.argv) > 2 else None   # ex. "12.5" : une seule image PNG
    if only:
        n = int(float(only) * FPS)
        Image.frombytes("RGB", (W, H), frame(n)).save(out)
        return
    nframes = int(round(T_TOTAL * FPS))
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out],
                          stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(frame, range(nframes), chunksize=4)):
            ff.stdin.write(buf)
            if k % 60 == 0:
                print(f"\r{k}/{nframes}", end="", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"\nvidéo : {out}")


if __name__ == "__main__":
    main()

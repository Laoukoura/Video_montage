"""Étape D : éléments graphiques (PNG transparents) générés avec Pillow.

Cartes de titre, mots-clés avec pictogramme, carte de conclusion. Aucune illustration
« sémantique » n'est inventée : seuls des pictogrammes géométriques sobres sont dessinés.
"""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import common

ACCENT = (255, 230, 0)
DARK = (16, 16, 24)
WHITE = (255, 255, 255)


def font(size):
    return ImageFont.truetype(common.find_font_file(), int(size))


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def draw_text(d, xy, text, fnt, fill=WHITE, anchor="la", stroke=0):
    d.text(xy, text, font=fnt, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(10, 10, 14))


def icon(d, kind, cx, cy, r, col):
    if kind == "arrow":
        d.polygon([(cx - r, cy - r * .35), (cx + r * .2, cy - r * .35), (cx + r * .2, cy - r * .8),
                   (cx + r, cy), (cx + r * .2, cy + r * .8), (cx + r * .2, cy + r * .35),
                   (cx - r, cy + r * .35)], fill=col)
    elif kind == "check":
        d.line([(cx - r * .7, cy), (cx - r * .2, cy + r * .55), (cx + r * .75, cy - r * .6)],
               fill=col, width=max(4, int(r * .35)), joint="curve")
    elif kind == "star":
        pts = [(cx + (r if i % 2 == 0 else r * .45) * math.sin(i * math.pi / 5),
                cy - (r if i % 2 == 0 else r * .45) * math.cos(i * math.pi / 5)) for i in range(10)]
        d.polygon(pts, fill=col)
    else:  # spark
        pts = [(cx, cy - r), (cx + r * .25, cy - r * .25), (cx + r, cy), (cx + r * .25, cy + r * .25),
               (cx, cy + r), (cx - r * .25, cy + r * .25), (cx - r, cy), (cx - r * .25, cy - r * .25)]
        d.polygon(pts, fill=col)


def gradient(W, H, y0, y1, a0, a1):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = g.load()
    for y in range(max(0, y0), min(H, y1)):
        a = int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0))
        for x in range(W):
            px[x, y] = (8, 8, 14, a)
    return g


def title_card(path, W, H, title, subtitle, vertical):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if vertical:
        img = Image.alpha_composite(img, gradient(W, H, 0, int(H * .38), 170, 0))
        d = ImageDraw.Draw(img)
        fnt = font(H * .046)
        lines = wrap(d, title.upper(), fnt, W * .84)[:3]
        y = int(H * .115)
        d.rounded_rectangle([W // 2 - 90, y - 38, W // 2 + 90, y - 28], 5, fill=ACCENT)
        for ln in lines:
            draw_text(d, (W // 2, y), ln, fnt, anchor="ma", stroke=5)
            y += int(fnt.size * 1.18)
        if subtitle:
            draw_text(d, (W // 2, y + 12), subtitle, font(H * .026), ACCENT, "ma", 3)
    else:  # YouTube : bandeau en haut à gauche, libère le bas pour les sous-titres
        img = Image.alpha_composite(img, gradient(W, H, 0, int(H * .36), 170, 0))
        d = ImageDraw.Draw(img)
        fnt = font(H * .062)
        lines = wrap(d, title.upper(), fnt, W * .56)[:3]
        h_total = len(lines) * int(fnt.size * 1.15)
        y = int(H * .07)
        x = int(W * .06)
        d.rounded_rectangle([x, y - 6, x + 14, y + h_total + 4], 6, fill=ACCENT)
        for ln in lines:
            draw_text(d, (x + 38, y), ln, fnt, stroke=4)
            y += int(fnt.size * 1.15)
        if subtitle:
            draw_text(d, (x + 38, y + 6), subtitle, font(H * .036), ACCENT, "la", 3)
    img.save(path)
    return img.size


def callout(path, text, kind, H):
    fnt = font(H * .034)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = int(tmp.textlength(text, font=fnt))
    pad, r = int(fnt.size * .55), int(fnt.size * .8)
    w, h = tw + pad * 3 + r * 2, int(fnt.size * 1.9)
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([24, 28, 24 + w, 28 + h], h // 2, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], h // 2, fill=DARK + (235,), outline=ACCENT, width=4)
    d.ellipse([20 + pad, 20 + h // 2 - r, 20 + pad + 2 * r, 20 + h // 2 + r], fill=ACCENT)
    icon(d, kind, 20 + pad + r, 20 + h // 2, r * .62, DARK)
    draw_text(d, (20 + pad * 2 + 2 * r, 20 + h // 2), text, fnt, anchor="lm")
    img.save(path)
    return img.size


def outro_card(path, W, H, title, cta, logo, vertical):
    img = Image.new("RGBA", (W, H), DARK + (215,))
    d = ImageDraw.Draw(img)
    fnt = font(H * (.05 if vertical else .075))
    lines = wrap(d, title.upper(), fnt, W * (.8 if vertical else .6))[:4]
    lh = int(fnt.size * 1.2)
    total = len(lines) * lh + (int(fnt.size * 1.5) if cta else 0) + (int(H * .12) if logo else 0)
    y = (H - total) // 2
    d.rounded_rectangle([W // 2 - 110, y - 36, W // 2 + 110, y - 26], 5, fill=ACCENT)
    for ln in lines:
        draw_text(d, (W // 2, y), ln, fnt, anchor="ma", stroke=4)
        y += lh
    if cta:
        y += int(fnt.size * .4)
        draw_text(d, (W // 2, y), cta, font(fnt.size * .6), ACCENT, "ma", 3)
        y += int(fnt.size * .9)
    if logo:
        lg = Image.open(logo).convert("RGBA")
        k = (H * .10) / lg.height
        lg = lg.resize((int(lg.width * k), int(lg.height * k)), Image.LANCZOS)
        img.alpha_composite(lg, ((W - lg.width) // 2, y + int(H * .02)))
    img.save(path)
    return img.size

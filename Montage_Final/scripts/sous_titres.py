"""Étape E : sous-titres animés mot par mot (ASS, intégrés à l'image par libass) + SRT.

Principe : pour chaque mot, UN événement ASS couvre exactement [début du mot, début du mot
suivant]. Dans cet événement, SEUL ce mot est jaune (+ rebond d'échelle) ; les autres restent
blancs. Le jaune est donc lié aux horodatages réels des mots, pas à la phrase entière.
"""
import re

YELLOW = "&H00E6FF&"   # ASS = BGR  -> RGB(255,230,0)
WHITE = "&HFFFFFF&"


def group_words(words, max_chars, max_words):
    """Groupes de lecture (≤ 2 lignes) calés sur le débit : coupe sur ponctuation / pause."""
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        n_chars = sum(len(x["w"]) + 1 for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        strong = re.search(r"[.?!…]['\"»)]*$", w["w"]) is not None
        soft = re.search(r"[,;:]['\"»)]*$", w["w"]) is not None
        pause = nxt is not None and nxt["s"] - w["e"] > 0.45
        full = len(cur) >= max_words or n_chars >= max_chars * 2 - 3
        if nxt is None or strong or pause or full or (soft and n_chars > max_chars):
            groups.append(cur)
            cur = []
    return groups


def split_lines(group, max_chars):
    """Une ou deux lignes équilibrées : retourne l'indice du premier mot de la 2e ligne (ou None)."""
    lens = [len(w["w"]) for w in group]
    if sum(lens) + len(lens) - 1 <= max_chars or len(group) < 2:
        return None
    best, bd = 1, 1e9
    for k in range(1, len(group)):
        d = abs(sum(lens[:k]) - sum(lens[k:]))
        if d < bd:
            best, bd = k, d
    return best


def _t(sec):
    cs = int(round(sec * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def make_ass(words, path, prof, font):
    W, H = prof["w"], prof["h"]
    upper = prof["upper"]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: K,{font},{prof['fs']},&H00FFFFFF,&H00FFFFFF,&H00141414,&H96000000,-1,0,0,0,100,100,3,0,1,{prof['outline']},{prof['shadow']},2,40,40,40,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    groups = group_words(words, prof["line_chars"], prof["group_words"])
    ev = []
    for gi, g in enumerate(groups):
        g_end = g[-1]["e"] + 0.25
        if gi + 1 < len(groups):
            g_end = min(g_end, groups[gi + 1][0]["s"])
        g_end = max(g_end, g[-1]["e"])
        brk = split_lines(g, prof["line_chars"])
        pos = f"{{\\an2\\pos({W // 2},{int(prof['y'] * H)})}}"
        for k, w in enumerate(g):
            s = w["s"] if k else g[0]["s"]
            e = g[k + 1]["s"] if k + 1 < len(g) else g_end
            if e - s < 0.04:
                e = s + 0.04
            parts = []
            for j, x in enumerate(g):
                t = x["w"].upper() if upper else x["w"]
                t = t.replace("{", "(").replace("}", ")")
                if j == k:
                    t = f"{{\\c{YELLOW}\\fscx114\\fscy114\\t(0,110,\\fscx104\\fscy104)}}{t}{{\\c{WHITE}\\fscx100\\fscy100}}"
                sep = "\\N" if brk is not None and j == brk else " "
                parts.append((sep if j else "") + t)
            fad = "\\fad(70,0)" if k == 0 else ""
            tag = pos[:-1] + fad + "}"
            ev.append(f"Dialogue: 0,{_t(s)},{_t(e)},K,,0,0,0,,{tag}{''.join(parts)}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "".join(ev))
    return len(ev)


def make_srt(words, path, max_chars=32, max_words=7):
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out = []
    for i, g in enumerate(group_words(words, max_chars, max_words), 1):
        out.append(f"{i}\n{ts(g[0]['s'])} --> {ts(g[-1]['e'] + 0.1)}\n{' '.join(w['w'] for w in g)}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

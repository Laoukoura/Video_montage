"""Étape C : sélection des passages, coupes sur les frontières de mots, plan de montage.

- les coupes ne tombent JAMAIS dans un mot (elles sont calées sur les horodatages des mots) ;
- pauses longues et mots de remplissage (euh, hum...) retirés ;
- accroche (cold open) choisie parmi les phrases réelles de l'intervenant ;
- zooms / mots-clés proposés automatiquement dans plan.json (modifiable à la main).

Sorties : intermediaires/cuts.json (segments + mots sur la timeline finale), intermediaires/plan.json
"""
import argparse
import re
import sys
from collections import Counter

import common
from common import DIRS, MontageError, log

FILLERS = {"euh", "heu", "hum", "hmm", "mmm", "uh", "um", "uhm", "ben", "bah"}
STOP = set("""les des une est que qui pour dans pas sur avec vous nous mais plus comme tout cette ces
son ses leur aux par ont être avoir fait faire très donc alors aussi quand même sans sous entre
the and that this with for are was have from your you not but they their what when will would
there which about into more than then them just like cest c'est qu'il qu'on j'ai""".split())


def clean(w):
    return re.sub(r"[^\wÀ-ÿ'’-]", "", w).lower()


def is_filler(w):
    return clean(w) in FILLERS


def sentences(words):
    """Découpe en phrases (indices) sur la ponctuation forte ou une longue pause."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        end = re.search(r"[.?!…]['\"»)]*$", w["w"]) is not None
        gap = words[i + 1]["s"] - w["e"] if i + 1 < len(words) and words[i + 1]["src"] == w["src"] else 9
        if end or gap > 0.9:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def pick_hook(words, total):
    """Phrase d'accroche réelle : 3-9 s, ≥ 6 mots, favorise ? ! et chiffres. None si vidéo courte."""
    if total < 30:
        return None
    best, best_score = None, 0
    for idx in sentences(words):
        a, b = words[idx[0]], words[idx[-1]]
        d = b["e"] - a["s"]
        if not (3 <= d <= 9 and len(idx) >= 6) or any(is_filler(words[i]["w"]) for i in idx):
            continue
        txt = " ".join(words[i]["w"] for i in idx)
        score = 1 + 0.1 * len(idx) + 2 * ("?" in txt) + 1.5 * ("!" in txt) + \
            sum(ch.isdigit() for ch in txt) * 0.2 + (0.5 if min(words[i]["p"] for i in idx) > 0.7 else -1)
        if score > best_score:
            best, best_score = idx, score
    return best


def plan_cuts(data, pad=0.15, max_gap=0.5, fillers=True, hook="auto", limit=None):
    words = sorted(data["words"], key=lambda w: (w["src"], w["s"]))
    dur = {f["src"]: f["duration"] for f in data["files"]}
    drop = [fillers and is_filler(w["w"]) for w in words]

    spans = []  # {src, s, e, words}
    last_kept = None
    for i, w in enumerate(words):
        if drop[i]:
            continue
        gap_ok = (spans and spans[-1]["src"] == w["src"] and last_kept == i - 1 and
                  w["s"] - spans[-1]["words"][-1]["e"] <= max_gap)
        if not gap_ok:
            spans.append({"src": w["src"], "words": []})
        spans[-1]["words"].append(w)
        last_kept = i
    # bornes : marge autour de la parole, réduite à côté d'un mot supprimé
    for sp in spans:
        a, b = sp["words"][0], sp["words"][-1]
        ia, ib = words.index(a), words.index(b)
        pa = 0.03 if ia > 0 and drop[ia - 1] else pad
        pb = 0.03 if ib + 1 < len(words) and drop[ib + 1] else pad
        sp["s"] = max(0.0, a["s"] - pa)
        sp["e"] = min(dur[sp["src"]], b["e"] + pb)
    for prev, sp in zip(spans, spans[1:]):  # pas de chevauchement
        if prev["src"] == sp["src"] and sp["s"] < prev["e"]:
            mid = (prev["words"][-1]["e"] + sp["words"][0]["s"]) / 2
            prev["e"], sp["s"] = min(prev["e"], mid), max(sp["s"], mid)
    spans = [s for s in spans if s["e"] - s["s"] >= 0.25]

    total_src = sum(s["e"] - s["s"] for s in spans)
    hook_span = None
    if hook == "auto":
        h = pick_hook(words, total_src)
        if h:
            hs = [words[i] for i in h]
            hook_span = {"src": hs[0]["src"], "s": max(0, hs[0]["s"] - 0.1),
                         "e": min(dur[hs[0]["src"]], hs[-1]["e"] + 0.15), "words": hs, "kind": "hook"}
    if hook_span:
        spans.insert(0, hook_span)

    segs, tl_words, off = [], [], 0.0
    for sp in spans:
        kept = sp["words"]
        end = sp["e"]
        if limit is not None and off + (end - sp["s"]) > limit:  # extrait test : coupe à un mot
            room = limit - off
            kept = [w for w in kept if w["e"] - sp["s"] <= room]
            if not kept:
                break
            end = kept[-1]["e"] + 0.1
        seg = {"src": sp["src"], "start": round(sp["s"], 3), "end": round(end, 3),
               "off": round(off, 3), "kind": sp.get("kind", "main")}
        segs.append(seg)
        for w in kept:
            tl_words.append({"w": w["w"], "s": round(off + w["s"] - sp["s"], 3),
                             "e": round(off + w["e"] - sp["s"], 3), "p": w.get("p", 1.0)})
        off += end - sp["s"]
        if limit is not None and off >= limit - 0.05:
            break
    cuts = {"segments": segs, "words": tl_words, "duration": round(off, 3),
            "hook_end": round(segs[0]["end"] - segs[0]["start"], 3) if segs and segs[0]["kind"] == "hook" else 0.0,
            "source_duration": round(sum(dur.values()), 3)}
    log.info("Montage : %.1fs gardées sur %.1fs (%d segments, accroche=%s)",
             off, cuts["source_duration"], len(segs), "oui" if cuts["hook_end"] else "non")
    return cuts


def auto_plan(cuts, title=None, cta=None, logo=None):
    """Zooms, mots-clés et titres proposés ; tout est modifiable dans plan.json."""
    words, total = cuts["words"], cuts["duration"]
    t_body = cuts["hook_end"]
    sents = sentences([{**w, "src": 0} for w in words])
    zooms, last_end = [], -99.0
    if cuts["hook_end"]:  # poussée lente sur toute l'accroche
        zooms.append({"t0": 0.0, "t1": max(0.5, cuts["hook_end"] - 0.5), "amp": 0.10, "in": 0.9, "out": 0.5})
    for k, idx in enumerate(sents):
        a, b = words[idx[0]]["s"], words[idx[-1]]["e"]
        if a < t_body + 1.0 or a - last_end < 5.0 or b - a < 2.0:
            continue
        txt = " ".join(words[i]["w"] for i in idx)
        if "!" in txt or "?" in txt:  # moment fort : rapprochement plus rapide
            z = {"t0": a, "t1": min(b, a + 1.6), "amp": 0.16, "in": 0.25, "out": 0.5}
        elif k % 3 == 1:              # explication : zoom lent et doux
            z = {"t0": a, "t1": b, "amp": 0.08, "in": 1.2, "out": 0.7}
        else:
            continue
        zooms.append(z)
        last_end = z["t1"]
    if not any(z["t0"] > t_body for z in zooms) and total > 6:  # garantit au moins un zoom
        zooms.append({"t0": t_body + 2.0, "t1": min(total - 1, t_body + 4.5), "amp": 0.12, "in": 0.5, "out": 0.6})

    cnt, first = Counter(), {}
    for w in words:
        c = clean(w["w"])
        if len(c) >= 5 and c not in STOP and w["s"] > t_body + 2.5:
            cnt[c] += 1
            first.setdefault(c, (w["s"], re.sub(r"[^\wÀ-ÿ'’ -]", "", w["w"])))
    ranked = sorted(cnt, key=lambda c: (-cnt[c], -len(c)))
    icons, callouts = ["spark", "arrow", "check", "star"], []
    want = max(1, int(total // 18))
    for c in ranked:
        t, txt = first[c]
        if all(abs(t - o["t"]) >= 7 for o in callouts):
            callouts.append({"t": round(t, 2), "dur": 1.9, "text": txt.upper(),
                             "icon": icons[len(callouts) % 4]})
        if len(callouts) >= want:
            break
    callouts.sort(key=lambda o: o["t"])

    auto_title = False
    if not title:
        title = " ".join(w["w"] for w in words[:7]).strip(" ,;:.") if words else "Titre"
        auto_title = True
    return {"title": title, "title_auto": auto_title, "subtitle": None,
            "title_t": round(t_body + 0.2, 2), "title_dur": 2.6,
            "zooms": zooms, "callouts": callouts,
            "outro": {"extra": 3.0, "title": title, "cta": cta, "logo": logo}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--title")
    ap.add_argument("--cta")
    ap.add_argument("--logo")
    ap.add_argument("--no-hook", action="store_true")
    ap.add_argument("--keep-fillers", action="store_true")
    ap.add_argument("--max-gap", type=float, default=0.5, help="pause max conservée (s)")
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--test-seconds", type=float, help="extrait test de N secondes")
    a = ap.parse_args(argv)
    common.setup_logging()
    data = common.load_json(DIRS["inter"] / "words.json")
    cuts = plan_cuts(data, a.pad, a.max_gap, not a.keep_fillers,
                     None if a.no_hook else "auto", a.test_seconds)
    plan = auto_plan(cuts, a.title, a.cta, a.logo)
    common.save_json(DIRS["inter"] / "cuts.json", cuts)
    common.save_json(DIRS["inter"] / "plan.json", plan)
    log.info("plan.json : %d zooms, %d mots-clés", len(plan["zooms"]), len(plan["callouts"]))


if __name__ == "__main__":
    try:
        main()
    except MontageError as e:
        sys.exit(f"ERREUR : {e}")

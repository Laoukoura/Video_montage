"""Pipeline complet : python run_all.py RUSHES... [options]"""
import argparse
import sys

import analyse as an
import common
import compose
import controle_qualite as qc
import montage_horizontal
import montage_vertical
import preparation
import transcription
from common import DIRS, MontageError, log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+", help="dossier de rushes ou fichiers (ordre alphabétique)")
    ap.add_argument("--lang")
    ap.add_argument("--whisper", default="small")
    ap.add_argument("--import-words", help="words.json déjà prêt (saute la transcription)")
    ap.add_argument("--title")
    ap.add_argument("--cta")
    ap.add_argument("--logo")
    ap.add_argument("--music")
    ap.add_argument("--font", help="nom de police libass (défaut : Arial Black sous Windows)")
    ap.add_argument("--focus-x", type=float)
    ap.add_argument("--no-hook", action="store_true")
    ap.add_argument("--vertical-mode", choices=["cover", "blurfit"], help="cover = recadrage plein cadre ; blurfit = vidéo entière sur fond flou")
    ap.add_argument("--no-gpu", action="store_true")
    ap.add_argument("--only", choices=["v", "h"])
    ap.add_argument("--test-seconds", type=float, help="extrait test (ex. 25) au lieu du rendu complet")
    ap.add_argument("--reuse-plan", action="store_true", help="réutilise plan.json édité à la main")
    a = ap.parse_args(argv)
    common.setup_logging()
    notes = []

    files = an.find_rushes(a.inputs)
    ana = an.analyse(files)
    analyse_d = {"files": ana}
    if a.import_words:
        data = common.load_json(a.import_words)
        notes.append("Transcription importée depuis un fichier (non produite par ce run).")
    else:
        data = transcription.transcribe(files, a.lang, a.whisper)
    common.save_json(DIRS["inter"] / "words.json", data)
    bad = transcription.doubtful(data)
    if bad:
        notes.append(f"{len(bad)} mot(s) à faible confiance Whisper : à relire dans intermediaires/words.json "
                     "(" + ", ".join(w["w"] for w in bad[:8]) + ("..." if len(bad) > 8 else "") + ")")

    cuts = preparation.plan_cuts(data, hook=None if a.no_hook else "auto", limit=a.test_seconds)
    plan_path = DIRS["inter"] / "plan.json"
    if a.reuse_plan and plan_path.exists():
        plan = common.load_json(plan_path)
    else:
        plan = preparation.auto_plan(cuts, a.title, a.cta, a.logo)
        common.save_json(plan_path, plan)
    common.save_json(DIRS["inter"] / "cuts.json", cuts)
    if plan.get("title_auto"):
        notes.append(f"Titre généré automatiquement ('{plan['title']}') : à remplacer avec --title.")

    cut = compose.cut_stage(cuts, analyse_d)
    results, kw = {}, dict(music=a.music, focus_x=a.focus_x, gpu=not a.no_gpu, font=a.font)
    suffix = "_TEST" if a.test_seconds else ""
    for fmt, mod in (("v", montage_vertical), ("h", montage_horizontal)):
        if a.only and a.only != fmt:
            continue
        prof = compose.PROFILES[fmt]
        out = DIRS[prof["dir"]] / prof["name"].replace(".mp4", f"{suffix}.mp4")
        mod.render(cuts, plan, analyse_d, cut, out=out,
                   mode=a.vertical_mode if fmt == "v" else None, **kw)
        results[fmt] = qc.check(fmt, out, cuts["duration"] + plan["outro"]["extra"],
                                {"title": plan["title_t"],
                                 "callout": plan["callouts"][0]["t"] if plan["callouts"] else 5})
    notes += ["Cadrage vertical : visage détecté seulement si OpenCV est installé, sinon centré (--focus-x).",
              "Illustrations : pictogrammes géométriques sur mots-clés ; pas d'illustrations sémantiques générées.",
              "Synchronisation : calée sur les horodatages Whisper ; vérification visuelle par images, "
              "pas d'écoute humaine automatique."]
    qc.write_report(results, notes)
    bad = [f for f, r in results.items() if not r["ok"]]
    if bad:
        sys.exit(f"Contrôle qualité en échec pour : {bad} (voir rapport/rapport_montage.txt)")
    for r in results.values():
        log.info("OK -> %s", r["fichier"])


if __name__ == "__main__":
    try:
        main()
    except MontageError as e:
        sys.exit(f"ERREUR : {e}")

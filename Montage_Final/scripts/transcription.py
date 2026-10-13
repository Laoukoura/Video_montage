"""Étape B : transcription avec horodatage de chaque mot (faster-whisper).

Les temps mot-à-mot viennent de l'alignement interne de Whisper (word_timestamps).
Chaque mot garde sa probabilité 'p' : les mots douteux (p < 0.45) sont listés pour relecture.

Usage :
  python transcription.py RUSH... [--lang fr] [--model small]
  python transcription.py RUSH... --import-json mots.json     # transcription déjà obtenue
Sortie : intermediaires/words.json
"""
import argparse
import sys

import common
from common import DIRS, MontageError, log, probe


def transcribe(files, lang=None, model_size="small"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise MontageError("faster-whisper absent : pip install faster-whisper "
                           "(ou fournir --import-json)")
    log.info("Chargement du modèle Whisper '%s' ...", model_size)
    try:
        model = WhisperModel(model_size, device="auto", compute_type="auto")
    except Exception as e:  # modèle non téléchargeable, pas de réseau...
        raise MontageError(f"Impossible de charger le modèle Whisper : {e}")
    words, meta = [], []
    for src, f in enumerate(files):
        log.info("Transcription : %s", f)
        segs, info = model.transcribe(str(f), language=lang, word_timestamps=True,
                                      vad_filter=True, beam_size=5)
        n = 0
        for s in segs:
            for w in s.words or []:
                t = w.word.strip()
                if t:
                    words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3),
                                  "p": round(w.probability, 2), "src": src})
                    n += 1
        meta.append({"src": src, "path": str(f), "duration": probe(f)["duration"],
                     "lang": info.language})
        log.info("  %d mots, langue détectée : %s", n, info.language)
    return {"files": meta, "words": words}


def doubtful(data, thr=0.45):
    return [w for w in data["words"] if w.get("p", 1) < thr]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--lang")
    ap.add_argument("--model", default="small")
    ap.add_argument("--import-json")
    a = ap.parse_args(argv)
    common.setup_logging()
    if a.import_json:
        data = common.load_json(a.import_json)
    else:
        data = transcribe(a.files, a.lang, a.model)
    common.save_json(DIRS["inter"] / "words.json", data)
    bad = doubtful(data)
    log.info("%d mots, dont %d à faible confiance (à relire dans words.json)",
             len(data["words"]), len(bad))


if __name__ == "__main__":
    try:
        main()
    except MontageError as e:
        sys.exit(f"ERREUR : {e}")

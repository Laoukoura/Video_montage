# Montage_Final — pipeline de montage autonome (FFmpeg + Python)

Prérequis : Python 3.10+, FFmpeg/FFprobe dans le PATH, `pip install pillow numpy faster-whisper`
(optionnel : `opencv-python` pour centrer le cadrage vertical sur le visage).

```
cd Montage_Final/scripts
# 1) extrait test de 25 s (sous-titres, zoom, mot-clé, SFX, intro/outro)
python run_all.py "C:\Users\...\Vidéaste" --lang fr --title "Mon titre" --test-seconds 25
# 2) rendus complets (vertical + horizontal)
python run_all.py "C:\Users\...\Vidéaste" --lang fr --title "Mon titre" --cta "Abonne-toi" --logo logo.png
```
Options : `--music fichier.mp3`, `--vertical-mode cover|blurfit`, `--focus-x 0.45`, `--no-hook`,
`--no-gpu`, `--only v|h`, `--import-words words.json`, `--reuse-plan` (après avoir édité
`intermediaires/plan.json` : zooms, mots-clés, titres). Les rushes ne sont jamais modifiés.
Rapport : `rapport/rapport_montage.txt`, journal : `rapport/execution.log`.

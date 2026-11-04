# Spot publicitaire — « Maîtrise le montage vidéo avec Claude AI »

Spot vertical **9:16, 1080×1920, 30 i/s, ~43 s** (TikTok, Reels, Facebook, WhatsApp).
Fichier final : `sortie/Spot_Claude_AI_9x16_1080p.mp4` (H.264 + AAC 192 k, −14 LUFS).

## Découpage (synchronisé sur la voix off)
| Temps | Plan | Narration | Mise en scène |
|---|---|---|---|
| 0,0–0,9 | Ouverture | — | Logo-éclat, « NOUVELLE FORMATION », trait de lumière, flash |
| 0,9–4,6 | Accroche (photo 3) | « Et si ton téléphone devenait un vrai studio de montage ? » | Zoom avant lent sur le visage, habillage caméra (REC, time-code), mots qui jaillissent |
| 4,6–10,2 | Claude AI (photo 1) | « Avec Claude AI, l'IA devient ton assistant de réalisation. » | Travelling vers le téléphone, **CLAUDE AI** avec halo, carte « Assistant de réalisation » qui se tape |
| 10,2–17,3 | Montage (illustration) | « Script, découpage, sous-titres, musique, effets… de A à Z. » | Smartphone avec appli de montage (aperçu, timeline qui défile), puces animées à chaque mot, **MONTAGE VIDÉO** |
| 17,3–22,9 | Mobile (photo 3) | « Sans ordinateur. Sans logiciel compliqué. Cent pour cent sur téléphone. » | Panoramique vers le geste, mots barrés, **100 % SUR TÉLÉPHONE** avec impact et secousse |
| 22,9–28,5 | Publier (illustration) | « …prêtes à publier sur TikTok, Reels et WhatsApp. » | Trois smartphones en éventail (vidéos qui jouent, j'aime qui montent) |
| 28,5–34,0 | Afrique (photo 2) | « Rejoins une formation pratique, en direct… » | Plan d'ensemble révélé depuis la scène, badge EN DIRECT |
| 34,0–43,4 | Appel à l'inscription | « Les places sont limitées. Inscris-toi dès maintenant… » | Portrait du formateur, PLACES LIMITÉES, bouton **JE M'INSCRIS** pulsé + tap |

Transitions : flash, whip-pan avec flou de bougé, zoom radial, light leak, glitch RVB.
Les photos ne sont que recadrées/étalonnées : visage et tenue noire du formateur intacts.

## Audio
* Voix off : Piper, voix neuronale française masculine `fr_FR-tom-medium` (texte dans `scripts/narration.py`).
* Musique : composition originale générée par `scripts/audio.py` (100 BPM, Am–F–C–G : pads, arpèges,
  piano, basse, batterie qui entre sur « Claude AI », pause sur « 100 % », final sur l'appel) — libre de droits.
* Bruitages : whoosh de transition, impacts sur les mots clés, pops, clics, risers. Ducking musique sous la voix.

## Regénérer
```bash
pip install pillow numpy piper-tts    # + ffmpeg
# modèle de voix : voix/fr_FR-tom-medium.onnx (+ .onnx.json), dépôt rhasspy/piper-voices
cd scripts && python run.py
```
Modifier le texte : `scripts/narration.py` (le calage plans/textes suit automatiquement).
Image test d'un instant : `python video.py test.png 12.5`.

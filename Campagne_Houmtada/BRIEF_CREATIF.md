# Campagne « La fraîcheur prend vie » — Yaourt aux fruits

Spot publicitaire 30 s · vertical 9:16 (1080×1920) · TikTok / Instagram Reels / Facebook Reels

> **Ce document prépare la production.** Claude ne génère pas la vidéo : les plans sont à produire avec
> des outils externes (section 10), puis à assembler avec `assembler.py` ou un logiciel de montage.

---

## 0. ⚠️ Points à valider AVANT de lancer la génération

| # | Point | Ce que montrent les références | Décision à prendre |
|---|-------|-------------------------------|--------------------|
| 1 | **Orthographe du nom** | Le brief écrit **HOUNTADA** (avec un **N**). L'étiquette du couvercle et tous les textes TikTok écrivent **Houmtada House** (avec un **M**). | Confirmer l'orthographe officielle. Ce document utilise **HOUMTADA HOUSE**, l'orthographe imprimée sur le produit réel, pour ne pas créer d'écart entre le texte à l'écran et l'étiquette. Si « Hountada » est la bonne orthographe, c'est l'étiquette qui est fausse et il faut le savoir avant de tourner. |
| 2 | **Parfums / recettes** | Fruits visibles : fraise, kiwi, raisin rouge, ananas, banane, mangue (ou pomme jaune). Garnitures : granola, couche chocolat/brownie, pâte à tartiner. Le nom du compte affiche aussi 🍇🥥🧀 (raisin, **noix de coco**, **fromage / cheesecake ?**). | Lister les recettes réelles de la gamme. Les prompts ci-dessous utilisent **fraise + kiwi + raisin rouge + ananas + banane** (la recette « hero » de la photo 1). Remplacer dans chaque prompt si besoin. |
| 3 | **Produit « hero »** | Deux contenants : **bol rond transparent + couvercle plat étiqueté** (photos 1, 2, 4) et **grand gobelet transparent à couvercle dôme** (photos 3, 5). | Recommandation : le **bol étiqueté** est le hero (c'est lui qui porte le logo). Le gobelet parfait apparaît en scène 4. |
| 4 | **Photo de référence HD** | Les captures fournies sont des captures TikTok basse définition, en biais, avec les icônes de l'interface. | Indispensable : photographier l'**étiquette à plat, de face, en pleine lumière**, et le bol sous 3 angles (face, ¾, dessus), sur fond neutre, en résolution maximale. |
| 5 | **Prix** | Les publications varient : 1500 / 2500 / 3000 / 5000 F selon les vidéos. | Ne pas afficher de prix dans le spot tant qu'ils ne sont pas confirmés. |
| 6 | **Pâte à tartiner** | Un pot de marque connue est visible en photo 2. | Ne jamais montrer de pot ou de logo d'une autre marque dans la pub. Parler de « couche chocolat ». |

---

## 1. Analyse du produit réel — éléments à respecter impérativement

### L'étiquette (photo 4) — élément le plus critique
- **Forme :** sticker **rond** collé sur le **couvercle transparent plat** du bol.
- **Contour :** fin liseré **rouge** sur tout le pourtour.
- **Fond :** blanc avec un léger lavis aquarelle **rose pâle et bleu ciel**.
- **Logo :** « **Houmtada** » en **écriture manuscrite / script rouge**, grande taille, en diagonale montante ; « **House** » plus petit, script rouge, sous la fin du mot, à droite.
- **Feuille :** petite **feuille rouge + feuille verte** au-dessus du début du logo.
- **Sous-titre :** « **Yaourt aux fruits** » en petit script rouge, en diagonale, sous le « H ».
- **Illustration :** amas de fruits photoréalistes en bas à gauche — **ananas au centre**, oranges/mandarines, pommes, poires vertes, kiwis/litchis ; petite fraise/fruit du dragon au-dessus.
- **Bandeau :** **ruban rouge en diagonale** en bas à gauche, icône **téléphone blanc** dans un cercle, texte blanc **« +235 63914698 »**.
- **Cachet :** petit **tampon circulaire vert** en bas à droite.
- **Couleurs de marque :** rouge vif, blanc, vert feuille.

### Les contenants
- **Bol :** rond, plastique **transparent**, bord droit, couvercle plat transparent ; le contenu est visible par les côtés.
- **Gobelet :** grand gobelet transparent avec **couvercle dôme** transparent (parfaits en couches, salade de fruits).
- Pas d'opercule aluminium, pas de pot opaque, pas de manchon carton, pas de cuillère de marque.

### Le contenu (ce qui fait vendre)
- **Couches visibles par le côté :** fond **chocolat / brownie**, puis **yaourt blanc crémeux**, puis fruits.
- **Dessus :** demi-rondelle de **kiwi**, **fraises** coupées, **raisins rouges** coupés en deux, dés d'**ananas** et de **banane**, parfois **granola** doré.
- **Aspect :** fait main, généreux, fruits frais légèrement brillants. **Pas** l'aspect industriel lisse d'un yaourt de supermarché : c'est l'authenticité « maison » qui différencie la marque.

### Interdits absolus (à répéter dans chaque prompt)
Pas de nouvel emballage · pas de logo réinventé · pas de nom déformé · pas de texte inventé sur l'étiquette ·
pas de pot opaque · pas de fruits absents de la recette · pas de marque tierce visible.

### ⚠️ Limite technique honnête
Aucun générateur vidéo actuel ne reproduit de façon fiable une écriture script fine comme « Houmtada » :
les lettres glissent ou changent d'une image à l'autre. **Méthode recommandée (pro) :**
1. **Plans produit (scènes 3, 4, 6) : filmer le vrai bol** (smartphone récent en 4K ou caméra, sur trépied, voir §5), **ou** générer en *image-to-video* à partir de la photo HD, puis
2. **remplacer l'étiquette en post-production** par la photo HD de la vraie étiquette, avec un suivi de mouvement (*planar tracking* : Mocha dans After Effects, ou suivi planaire de DaVinci Resolve Fusion ; à défaut, suivi d'objet de CapCut sur un plan stable).
3. Les scènes 1 et 2 (fruits + vague de yaourt) n'affichent pas le logo : elles se prêtent parfaitement à la génération IA.

---

## 2. Concept créatif définitif

**« HOUMTADA HOUSE — LA FRAÎCHEUR PREND VIE »**

Les fruits frais de N'Djamena se réveillent dans le noir, s'envolent, rencontrent une vague de yaourt
crémeux… et tout ce mouvement se pose dans **le vrai bol Houmtada House**. Le spot passe du spectacle
(scènes 1 à 3) au réel (scènes 4 et 5) : la magie de la pub, mais un produit **fait main**, que l'on
partage en famille. Le spot se termine sur le logo réel.

**Ton :** gourmand, lumineux, chaleureux. Premium sans être froid.
**Palette :** noir profond → blanc crème → rouge Houmtada → vert kiwi. Le rouge de la marque guide l'œil
jusqu'au logo final.
**Fil conducteur visuel :** **la demi-rondelle de kiwi** (signature visible sur la photo 1). Elle ouvre le spot
(premier fruit à traverser le cadre) et le referme (posée sur le bol final).

---

## 3. Storyboard minuté

| Temps | Scène | Image | Son | Texte à l'écran |
|-------|-------|-------|-----|-----------------|
| 0,0–3,0 | 1 · Le choc visuel | Noir. Un filet de lumière. Une rondelle de kiwi traverse le cadre au ralenti, puis fraises, raisins, dés d'ananas ; gouttelettes scintillantes. Poussée caméra rapide vers le centre. | Grave sourd + « whoosh » | — |
| 3,0–7,0 | 2 · L'explosion de fraîcheur | Les fruits tournent en apesanteur ; une vague de yaourt blanc forme une courbe autour d'eux. Travelling circulaire. | La musique démarre, éclaboussures | — |
| 7,0–12,0 | 3 · La révélation | La vague retombe et dévoile le **vrai bol Houmtada House**, au centre, étiquette lisible. Lente avancée caméra. | Montée musicale, accent sur la révélation | « HOUMTADA HOUSE » (discret, 9,5–11,5 s) |
| 12,0–18,0 | 4 · La signature gourmande | 3 gros plans : couches vues de côté (chocolat / yaourt / fruits) · cuillère qui plonge · gobelet parfait à couvercle dôme. | Rythme établi, sons de cuillère | « Fait main. Fruits frais. » |
| 18,0–25,0 | 5 · Le plaisir à partager | Salon chaleureux à N'Djamena, lumière de fin d'après-midi. Deux personnes ouvrent le bol, goûtent, sourient. Produit visible. | Musique plus douce, rires légers | — |
| 25,0–30,0 | 6 · La signature finale | Le bol hero, entouré des fruits de la recette, sur fond crème et rouge. Avancée lente. Logo réel lisible. | Signature sonore (2 notes + « pop » de couvercle) | « HOUMTADA HOUSE » / « La fraîcheur prend vie » / « Découvrez votre plaisir fruité. » |

---

## 4. Prompts vidéo autonomes (un par scène)

> **Pourquoi en anglais :** les générateurs vidéo (Veo, Kling, Runway, Sora, Hailuo…) suivent nettement
> mieux les consignes de caméra et de lumière rédigées en anglais. Les textes **affichés** restent en français
> et sont ajoutés au montage, **jamais** dans la génération.
>
> **Réglages communs :** 9:16 · 1080×1920 minimum · 24 ou 30 i/s · générer 2 à 4 variantes par scène et garder la meilleure.
> Coller le bloc **NEGATIVE** dans le champ négatif, ou à la fin du prompt si l'outil n'en a pas.

**Bloc NEGATIVE (commun) :**
```
no text, no captions, no watermark, no invented logo, no altered brand name, no opaque cup, no foil lid,
no cardboard sleeve, no third-party brands, no cartoon look, no plastic-looking fruit, no CGI sheen,
no extra fingers, no deformed hands, no warping, no flicker, no color shift between frames
```

### Scène 1 — Le choc visuel (0–3 s) · *text-to-video*
```
Vertical 9:16 premium food commercial, macro cinematography. Opening on near-total darkness, a single
thin rim light from the upper right. A fresh half-slice of green kiwi with black seeds flies across the
frame from left to right in extreme slow motion (1000 fps look), followed by halved fresh strawberries,
halved red grapes and small golden pineapple cubes. Tiny water droplets detach from the fruit and
sparkle like crystals in the rim light. The camera performs a fast push-in toward the center of the
frame, ending sharp on the kiwi slice. Deep black background, shallow depth of field, natural fruit
textures with visible pulp fibers and seeds, photorealistic, shot on high-speed camera with a 100mm
macro lens, high contrast, rich saturated but natural colors.
```

### Scène 2 — L'explosion de fraîcheur (3–7 s) · *text-to-video* (ou *image-to-video* depuis la dernière image de la scène 1)
```
Vertical 9:16 premium dairy commercial. Fresh strawberry halves, kiwi slices, red grape halves, pineapple
cubes and banana slices float and rotate slowly in mid-air against a soft dark-to-cream gradient
background. A thick, silky wave of white creamy yogurt sweeps through the frame in an elegant curving
ribbon, wrapping around the fruit. Realistic fluid simulation: viscous, glossy yogurt with natural
splash crowns and small droplets, physically accurate gravity and surface tension. The camera performs a
smooth 180-degree orbit around the action at fruit level. Soft key light from above, warm rim light from
behind, small specular highlights on the yogurt surface. Ultra-realistic, high-speed slow motion,
appetizing, clean, no clutter.
```

### Scène 3 — La révélation du produit (7–12 s) · *image-to-video* **obligatoire**
**Image de départ :** la photo HD du **vrai bol Houmtada House** (étiquette face caméra), détourée et
posée sur un fond crème clair (retouche Photoshop / Photopea ou un outil d'édition d'image avec référence produit).
```
Vertical 9:16 premium commercial product reveal. Use the provided image as the exact product: a round
clear plastic yogurt bowl with a flat clear lid and a round white sticker label with red script lettering.
Keep the packaging, the label, the lettering, the colors and the proportions exactly identical to the
reference image, do not redraw or change any text. A wave of white yogurt and a few fruit pieces
(strawberry, kiwi, red grape) fall away from the bowl and gently settle around its base, progressively
revealing it in the center of the frame. Slow, steady camera dolly-in toward the bowl. Studio lighting:
large soft key from front-left, warm rim light outlining the bowl's edges, subtle reflection on a glossy
cream surface. Visible layers through the transparent side: chocolate base, white yogurt, colorful fresh
fruit on top. Photorealistic, elegant, high-end advertising look.
```
➡️ **Post-production :** remplacer l'étiquette par la vraie (suivi planaire) sur toute la durée du plan.

### Scène 4 — La signature gourmande (12–18 s) · **3 plans de 2 s** · tournage réel recommandé, sinon *image-to-video* depuis les photos réelles

**4a — Les couches (12–14 s)**
```
Vertical 9:16 macro food commercial. Extreme close-up side view through the transparent wall of a round
clear yogurt bowl: a dark chocolate cake base at the bottom, a thick layer of creamy white yogurt, and
fresh fruit on top (halved strawberries, kiwi slice, halved red grapes). Slow lateral tracking shot from
left to right along the bowl wall. Soft backlight making the yogurt glow, tiny condensation droplets on
the plastic. Shallow depth of field, 100mm macro, photorealistic, homemade artisanal look.
```
**4b — La cuillère (14–16 s)**
```
Vertical 9:16 macro food commercial, top-down 45-degree angle. A metal spoon slowly dives into a bowl of
creamy white yogurt topped with fresh strawberries, kiwi and red grapes, and lifts a generous spoonful
showing the yogurt texture and the chocolate layer underneath. Slow motion, smooth glossy yogurt,
natural fruit juice. Warm soft key light, creamy background bokeh, photorealistic, appetizing.
```
**4c — Le gobelet parfait (16–18 s)** — *image-to-video* depuis la photo 5
```
Vertical 9:16 premium food commercial. Use the provided image as the exact product: a tall clear plastic
cup with a clear dome lid, filled with alternating layers of chocolate cake chunks and thick vanilla
cream yogurt. Keep the cup and layers exactly as in the reference. Slow 90-degree turntable rotation,
camera slightly below cup level, soft backlight making the cream glow, warm rim light, cream-colored
seamless background, photorealistic, high-end advertising look.
```

### Scène 5 — Le plaisir à partager (18–25 s) · **tournage réel fortement recommandé**
Les visages et les mains générés par IA restent la première source d'aspect « faux », et le public
local reconnaît immédiatement un décor ou une personne qui ne sonnent pas juste. Filmer de vraies personnes
(avec leur **autorisation écrite de droit à l'image**), en mouvement naturel, sans témoignage parlé.
Si la génération est imposée, prompt :
```
Vertical 9:16 lifestyle food commercial, warm and authentic. A bright, welcoming living room in
N'Djamena, Chad, late-afternoon golden sunlight through a window with light patterned curtains. Two
young Chadian friends sit together on a sofa; one opens a round clear yogurt bowl (fresh strawberries,
kiwi and red grapes visible on top) and offers it to the other. They each take a spoonful, taste, and
share a natural, subtle smile and a quiet laugh, no exaggerated reactions. The bowl stays clearly visible
in the foreground. Handheld but stable camera, gentle slow push-in, 35mm lens, shallow depth of field,
soft natural skin tones, realistic hands holding the spoon correctly, five fingers per hand,
photorealistic, natural colors.
```
➡️ Plan de coupe conseillé (22–25 s) : gros plan du bol tenu entre deux mains, la cuillère qui se lève.

### Scène 6 — La signature finale (25–30 s) · *image-to-video* **obligatoire** + étiquette remplacée en post
```
Vertical 9:16 premium commercial end shot. Use the provided image as the exact product: a round clear
yogurt bowl with a flat clear lid and the round white sticker label with red script lettering, kept
exactly identical to the reference, no redrawn text. The bowl stands in the center on a glossy cream
surface, label facing camera. Fresh strawberries, a kiwi half-slice, red grapes and pineapple cubes are
delicately arranged around its base, with a few water droplets. Background: soft cream gradient with a
subtle warm red glow behind the bowl. Slow, precise camera push-in, ending perfectly still for the
last 2 seconds. Elegant studio lighting, soft key from front, red-tinted rim light, gentle sparkle on
the droplets. Photorealistic, premium, clean composition with empty space in the top third for text.
```

---

## 5. Instructions de mouvement de caméra

| Scène | Mouvement | Objectif | Vitesse | Point clé |
|-------|-----------|----------|---------|-----------|
| 1 | *Push-in* rapide (accélère puis freine) | Macro 100 mm | Ralenti 4–8× | Finit net sur le kiwi → raccord avec la scène 2 |
| 2 | Orbite 180° à hauteur des fruits | 50–85 mm | Ralenti 2–4× | Le sens de l'orbite (gauche → droite) prolonge le mouvement de la scène 1 |
| 3 | *Dolly-in* lent et constant | 85 mm | Temps réel | Aucune secousse ; l'étiquette reste plane et face caméra (facilite le suivi) |
| 4a | Travelling latéral le long de la paroi | Macro 100 mm | Ralenti 2× | Slider ou rail ; mise au point sur la couche de yaourt |
| 4b | Fixe en plongée à 45° | 85–100 mm | Ralenti 4× (120 i/s) | La cuillère sort par le haut du cadre |
| 4c | Plateau tournant 90°, caméra fixe | 50 mm | Temps réel | Contre-plongée légère : le gobelet paraît « monumental » |
| 5 | Caméra épaule stabilisée, *push-in* doux | 35 mm | Temps réel | Le bol toujours au premier tiers inférieur |
| 6 | *Push-in* lent puis **arrêt complet 2 s** | 85 mm | Temps réel | Le cadre fixe final laisse lire le logo et les textes |

**Tournage réel au smartphone :** mode 4K 30 i/s (60 ou 120 i/s pour les ralentis), exposition et mise au point verrouillées,
trépied, lumière jamais en provenance du plafond seul, nettoyer couvercle et paroi avant chaque prise (traces de doigts).

---

## 6. Instructions d'éclairage

- **Scène 1 :** fond noir, **une seule lumière rasante** dure (contre-jour ¾ arrière droit) → gouttes qui scintillent. Rapport de contraste élevé.
- **Scène 2 :** passage progressif au clair : **grande source douce en plongée** (softbox ou fenêtre diffusée) + **contre-jour chaud** (3200 K) pour détacher la vague de yaourt.
- **Scène 3 et 6 :** éclairage « produit » : **key douce** avant gauche, **deux rims** latéraux pour dessiner le bord transparent du bol, **réflecteur blanc** en face pour faire lire l'étiquette, sans reflet sur le couvercle (inclinaison de 5–10° du couvercle ou polarisant). Scène 6 : léger halo **rouge** derrière le bol (gélatine rouge ou LED RVB) pour rappeler la marque.
- **Scène 4 :** **contre-jour** pour faire « briller » le yaourt à travers la paroi, réflecteur doré pour réchauffer les fruits.
- **Scène 5 :** **lumière naturelle de fin d'après-midi** par une fenêtre, complétée par un réflecteur pour les visages. Ne pas sous-exposer les peaux foncées : exposer pour les visages et non pour la fenêtre.
- **Température globale :** froid/neutre (scène 1) → chaud (scènes 5–6). Une seule étalonnage final (LUT commune) appliqué aux 6 scènes pour la continuité.

---

## 7. Plan de montage et transitions

Tempo musical conseillé : **120 BPM** → 1 temps = 0,5 s, 1 mesure = 2 s. Toutes les coupes tombent sur un temps.

| Passage | Moment | Transition | Raison |
|---------|--------|-----------|--------|
| 1 → 2 | 3,0 s | **Raccord mouvement** (le *push-in* de la scène 1 continue dans l'orbite de la scène 2), fondu ultra-court 0,2 s | Continuité de la vitesse |
| 2 → 3 | 7,0 s | **Volet par la vague** : la vague de yaourt passe devant l'objectif et révèle le bol (*wipe* vers le haut, 0,4 s) | La révélation « sort » de l'explosion |
| 3 → 4a | 12,0 s | **Coupe franche** sur le temps fort | Changement de rythme |
| 4a → 4b → 4c | 14,0 s et 16,0 s | **Coupes franches** toutes les mesures | Rythme gourmand |
| 4 → 5 | 18,0 s | **Fondu enchaîné doux** 0,5 s | On passe du studio au réel, à la chaleur humaine |
| 5 → 6 | 25,0 s | **Fondu au blanc crème** 0,3 s | Retour au studio pour la signature |

**Ralentis :** uniquement scène 1 (fruits), scène 2 (vague), scène 4b (cuillère). Scènes 3, 5, 6 en temps réel.
**Étalonnage :** même LUT pour toutes les scènes, saturation des rouges contrôlée (le rouge de l'étiquette ne doit pas « baver »).
**Zones de sécurité TikTok/Reels :** ne rien placer d'important dans les **250 px du bas** (légende, pseudo), les **130 px de droite** (icônes) et les **180 px du haut**. Le bol et les textes restent dans la zone centrale.

---

## 8. Voix off (optionnelle)

Recommandation : **version sans voix off** comme version principale (le visuel et la musique suffisent ; mieux pour le visionnage sans son). Version alternative avec voix off chaleureuse et posée, en français (une version en arabe tchadien est un vrai plus local) :

| Temps | Texte |
|-------|-------|
| 7,5 s | « Houmtada House. » |
| 12,5 s | « Des fruits frais, un yaourt onctueux… préparé à la main. » |
| 19,0 s | « Le plaisir se partage. » |
| 26,0 s | « Houmtada House. La fraîcheur prend vie. » |

Prévoir 0,5 s de musique seule avant et après chaque phrase. Baisser la musique de 8 à 10 dB sous la voix (*ducking*).

---

## 9. Plan sonore

| Temps | Musique | Effets sonores (SFX) |
|-------|---------|----------------------|
| 0,0 | Silence → **grave sourd** (*sub drop*) | Souffle léger, tintement cristallin quand les gouttes scintillent |
| 0,5–3,0 | Nappe tendue, intrigante | **Whoosh** à chaque fruit qui traverse, petite éclaboussure d'eau |
| 3,0 | **Entrée du rythme** (groove afro-pop / amapiano léger, 120 BPM) | Swoosh d'orbite |
| 3,5–7,0 | Montée | **Éclaboussure crémeuse** (son épais, pas d'eau), petites gouttes |
| 7,0–12,0 | **Montée et accent** sur la révélation (7,5 s) | « Shimmer » doux sur la lumière qui dessine le bol |
| 12,0–18,0 | Groove plein | Cuillère dans le yaourt (son crémeux), couvercle qui claque légèrement, croquant du granola |
| 18,0–25,0 | Version plus douce (filtre passe-bas léger) | Ambiance salon, rires légers, cuillère |
| 25,0–28,0 | Retour au plein | **Signature sonore : deux notes ascendantes + « pop » de couvercle** à 26,0 s |
| 28,0–30,0 | Résolution, fin propre sur un temps | — |

**Niveau final :** −14 LUFS intégré, crête −1 dBTP (norme des plateformes sociales).
**Droits :** utiliser une musique **sous licence commerciale** (bibliothèque payante : Artlist, Epidemic Sound…, ou générateur IA avec licence commerciale explicite, comme les offres payantes de Suno ou d'ElevenLabs Music). Les sons « tendance » de TikTok ne sont **pas** autorisés pour une publicité payante.

---

## 10. Textes à afficher

Police conseillée : un **script rouge** proche du logo pour « Houmtada House » est à **éviter** (ne pas imiter le logo). Utiliser le **vrai logo** (détouré depuis la photo HD de l'étiquette) + une linéale élégante (Montserrat, Poppins, ou Inter) pour le reste.

| Temps | Texte | Style |
|-------|-------|-------|
| 9,5–11,5 s | HOUMTADA HOUSE | Petites capitales blanches espacées, en haut, discret |
| 12,5–17,5 s | Fait main. Fruits frais. | Blanc, moyen, apparition en fondu |
| 25,5–30,0 s | **Logo réel** (image détourée) | Au-dessus du bol |
| 26,3–30,0 s | La fraîcheur prend vie | Rouge Houmtada, gras |
| 27,3–30,0 s | Découvrez votre plaisir fruité. | Blanc ou noir selon le fond, plus petit |
| 27,8–30,0 s *(option)* | Livraison partout à N'Djamena · 63 91 46 98 | Bandeau rouge, texte blanc (repris de la communication officielle) |

Les slogans « La fraîcheur prend vie » et « Découvrez votre plaisir fruité » sont des **propositions** : à valider par la marque avant diffusion.
Le spot ne contient **aucun témoignage** ni citation attribuée à une personne.

---

## 11. Outils externes et méthode d'assemblage

### Chaîne de production
| Étape | Outils possibles | Usage |
|-------|------------------|-------|
| Photo de référence | Smartphone + lumière du jour diffusée | Étiquette à plat + bol sous 3 angles (§0, point 4) |
| Images de départ (keyframes) | Photoshop / Photopea, ou un éditeur d'image IA avec référence produit (Nano Banana, GPT Image, Flux Kontext…) | Poser le **vrai** bol dans le décor des scènes 3 et 6 **sans le redessiner** |
| Génération vidéo | Google Veo, Kling, Runway, Hailuo, Sora… (mode *image-to-video* pour les scènes 3, 4c, 6) | 2 à 4 variantes par scène, garder la meilleure |
| Tournage réel | Smartphone 4K + trépied + réflecteur | Scènes 4 et 5 (recommandé) |
| Remplacement d'étiquette | After Effects + Mocha, DaVinci Resolve (Fusion), à défaut CapCut | Scènes 3, 4, 6 |
| Agrandissement / netteté | Topaz Video AI (optionnel) | Monter les plans générés en 1080×1920 propre |
| Musique et effets | Bibliothèque sous licence, ElevenLabs (effets sonores) | §9 |
| Montage final | CapCut (simple), DaVinci Resolve (pro, gratuit), ou `assembler.py` de ce dossier | §7 |

### Assemblage automatique avec `assembler.py`
Nommer les plans finaux `scene1.mp4` … `scene6.mp4` (scène 4 = les 3 gros plans déjà montés bout à bout) dans un dossier, puis :
```
python assembler.py plans/ houmtada_30s.mp4 --musique musique.mp3 --sfx sfx.wav --logo logo.png --police Montserrat-Bold.ttf
```
Le script :
1. normalise chaque plan en 1080×1920, 30 i/s (recadrage centré) ;
2. coupe chaque scène à sa durée du storyboard (3 / 4 / 5 / 6 / 7 / 5 s) ;
3. enchaîne les transitions du §7 aux temps exacts (3, 7, 12, 18, 25 s) ;
4. ajoute les textes du §10 et le logo sur la fin ;
5. mixe musique + piste d'effets, fondu de sortie, normalisation −14 LUFS ;
6. exporte en H.264 High, AAC 320 kb/s, `+faststart`, durée 30,0 s exacte.

Options : `--sans-textes` (version pour ajouter les textes dans CapCut), `--option-livraison` (bandeau livraison + téléphone).
Si un plan est trop court, sa dernière image est prolongée automatiquement (un avertissement s'affiche).

### Export manuel (CapCut / Resolve)
1080×1920 · 30 i/s · H.264 · 15–20 Mb/s · AAC 48 kHz · −14 LUFS · 30,0 s.
Exporter aussi une **version 4:5 (1080×1350)** pour le fil Facebook/Instagram, et une miniature (image de la scène 6).

### Contrôle qualité avant publication
- [ ] Le nom sur l'étiquette est identique à la photo réelle sur **chaque** image des scènes 3, 4 et 6 (lecture image par image).
- [ ] Aucune lettre qui « glisse », aucun texte inventé.
- [ ] Les fruits visibles = ceux de la recette réelle.
- [ ] Mains : 5 doigts, prise de cuillère correcte.
- [ ] Aucune marque tierce visible.
- [ ] Textes hors des zones masquées par l'interface TikTok/Reels.
- [ ] Lisible sans le son (premier plan percutant, logo final lisible).
- [ ] Musique sous licence commerciale, autorisations de droit à l'image signées.

"""
gemini_coach.py
===============
Module IA — génère un briefing cycliste complet via Google Gemini.
"""

import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


def generer_briefing(
    api_key:         str,
    dist_tot:        float,
    d_plus:          float,
    temps_s:         float,
    calories:        int,
    score:           dict,
    ascensions:      list,
    analyse_meteo:   dict,
    resultats:       list,
    heure_depart:    str,
    heure_arrivee:   str,
    vitesse_moyenne: float,
    infos_soleil:    dict,
    contexte_date:   str,
    nb_points_eau:   int  = 0,
    uv_pollen:       dict = None,
) -> str | None:
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        dist_km  = round(dist_tot / 1000, 1)
        d_plus_m = int(d_plus)
        duree_h  = round(temps_s / 3600, 2)
        dh       = int(duree_h)
        dm       = int((duree_h % 1) * 60)

        lever_str   = infos_soleil["lever"].strftime("%H:%M")   if infos_soleil else "inconnue"
        coucher_str = infos_soleil["coucher"].strftime("%H:%M") if infos_soleil else "inconnue"

        if ascensions:
            cols_str = "\n".join([
                f"  • {a.get('Nom','—')} ({a['Catégorie']}) — "
                f"Km {a['Départ (km)']}→{a['Sommet (km)']}, "
                f"{a['Longueur']}, D+ {a['Dénivelé']}, "
                f"pente moy. {a['Pente moy.']}, max {a['Pente max']}, "
                f"sommet {a.get('Alt. sommet','?')}, "
                f"arrivée sommet vers {a.get('Arrivée sommet','?')}"
                for a in ascensions
            ])
        else:
            cols_str = "  Aucune ascension catégorisée — parcours principalement roulant."

        valides = [cp for cp in resultats if cp.get("temp_val") is not None]
        if valides:
            t_min = min(cp["temp_val"] for cp in valides)
            t_max = max(cp["temp_val"] for cp in valides)
            t_moy = round(sum(cp["temp_val"] for cp in valides) / len(valides), 1)
            temp_txt = f"{t_min}°C min / {t_moy}°C moy / {t_max}°C max"
            ressentis = [cp["ressenti"] for cp in valides if cp.get("ressenti") is not None]
            ressenti_txt = (f"Wind chill : {min(ressentis)}°C à {max(ressentis)}°C"
                            if ressentis else "Pas de wind chill significatif")
        else:
            t_min = t_max = t_moy = None
            temp_txt = ressenti_txt = "Données indisponibles"

        if analyse_meteo:
            pct_face = analyse_meteo['pct_face']
            pct_dos  = analyse_meteo['pct_dos']
            pct_cote = analyse_meteo['pct_cote']
            vent_txt = f"{pct_face}% face / {pct_dos}% dos / {pct_cote}% côté"
            segs = analyse_meteo.get("segments_face", [])
            if segs:
                vent_txt += " — segments face : " + ", ".join(f"Km {s[0]}→{s[1]}" for s in segs)
            if analyse_meteo.get("premier_pluie"):
                cp_p = analyse_meteo["premier_pluie"]
                pluie_txt = f"RISQUE à {cp_p['Heure']} (Km {cp_p['Km']}, {cp_p.get('pluie_pct','?')}%)"
            else:
                pluie_txt = "Aucun risque >50% prévu"
        else:
            vent_txt = pluie_txt = "Indisponible"

        vents   = [cp.get("vent_val") for cp in valides if cp.get("vent_val") is not None]
        vent_max = max(vents) if vents else 0

        if uv_pollen:
            uv_txt    = uv_pollen.get("uv_label", "Inconnu")
            uv_max_val = uv_pollen.get("uv_max")
            pollen_txt = ", ".join(uv_pollen.get("pollens", [])) or "Aucune alerte"
        else:
            uv_txt = pollen_txt = "Indisponible"
            uv_max_val = None

        eau_txt = (f"{nb_points_eau} point(s) d'eau sur le tracé (OSM)"
                   if nb_points_eau > 0
                   else "Aucun point d'eau identifié — prévoir toute l'autonomie")

        if t_max is not None and t_max >= 25:
            eau_h = 1.0; eau_conseil = "1 bidon/heure + électrolytes (chaleur)"
        elif t_max is not None and t_max >= 15:
            eau_h = 0.7; eau_conseil = "700 ml/heure"
        else:
            eau_h = 0.5; eau_conseil = "500 ml/heure"
        eau_total = round(eau_h * duree_h, 1)

        carbs_h = 70 if (d_plus_m > 1500 or duree_h > 4) else 60
        carbs_total = int(carbs_h * duree_h)
        nb_barres = round(carbs_total / 40)
        nb_gels   = round(carbs_total / 25)

        prompt = f"""
Tu es à la fois un ami de longue date, un grand frère de route et un coach cycliste qui a tout vécu — les cols sous la neige, les crampes à 10 km du sommet, les coups de chaud en plaine. Tu connais la souffrance et le plaisir du vélo de l'intérieur. Tu tutoies le coureur, tu lui parles comme à quelqu'un que tu aimes et que tu respectes. Tu es chaleureux, humain, parfois cash, jamais condescendant. Tu as de l'humour mais tu sais être sérieux quand ça compte. Pas de langue de bois, pas de formules vides — chaque mot que tu écris, c'est ce que tu dirais vraiment à quelqu'un avant qu'il parte seul sur la route.

Règles absolues :
- Sois précis et chiffré — chaque conseil s'appuie sur une donnée concrète
- N'utilise que les données fournies, ne les répète jamais dans deux sections
- Le vent DOIT apparaître dans le plan de course : cite les segments exacts de vent de face/dos et leur impact tactique
- Commence directement par ## 📋 Résumé, sans phrase d'intro ni salutation générique ("Salut mon gars", "Alors,", etc.)

═══════════════════════════════════════════════
DONNÉES DE LA SORTIE
═══════════════════════════════════════════════
Date         : {contexte_date}
Distance     : {dist_km} km  |  D+ : {d_plus_m} m
Durée est.   : {dh}h{dm:02d}  |  Départ : {heure_depart}  |  Arrivée : {heure_arrivee}
Vitesse moy. : {vitesse_moyenne} km/h  |  Calories : {calories} kcal
Score        : {score['label']} ({score['total']}/10)

ASCENSIONS
{cols_str}

MÉTÉO
Températures : {temp_txt}
Ressenti     : {ressenti_txt}
Vent         : {vent_txt}  (max {vent_max} km/h)
Pluie        : {pluie_txt}
UV           : {uv_txt}
Pollen       : {pollen_txt}
Lever/Coucher: {lever_str} / {coucher_str}

LOGISTIQUE
Points d'eau : {eau_txt}
Eau calculée : {eau_total} L ({eau_conseil})
Glucides     : {carbs_total} g ({carbs_h}g/h) → {nb_barres} barres (40g) ou {nb_gels} gels (25g)

═══════════════════════════════════════════════
BRIEFING — RESPECTE EXACTEMENT CETTE STRUCTURE
═══════════════════════════════════════════════

## 📋 Résumé
3 phrases max. Accrocheur, pas bateau. Distance, D+, durée, départ/arrivée, niveau réel.
Si les noms de cols permettent d'identifier un massif ou une région, cite-le avec le ton d'un local.
Donne le ton de la sortie en une phrase qui claque — le coureur doit savoir à quoi s'attendre.

---

## 🌤️ Météo & Équipement

**Conditions du jour**
Synthèse température en 2 phrases : fourchette min/max, tendance sur la journée.

**Vent**
Section dédiée au vent — obligatoire, même si vent faible.
Données : {vent_txt} (rafales max {vent_max} km/h).
Explique l'impact concret sur la sortie : sur quelles portions il sera de face, de dos, de côté.
Le coureur roule SEUL — pas de roue, pas de peloton. Adapte les conseils en conséquence :
- Vent de face : réduire la cadence, adopter une position plus aéro (baisser les coudes, rentrer la tête), ne pas se battre contre lui
- Vent de dos : profiter pour récupérer ou placer une relance sans effort supplémentaire
- Vent de côté : vigilance sur la tenue de trajectoire, surtout en descente
Donne le ressenti global : est-ce que le vent est une contrainte majeure ce jour-là ou un facteur mineur ?

**Tenue**
Sois très précis : liste chaque pièce vestimentaire adaptée à t_min={t_min}°C au départ.
Mentionne si les descentes nécessitent un coupe-vent (haute altitude ou vent fort).

**Alertes**
- Pluie : {pluie_txt}. Conduite à tenir concrète si ça arrive.
- UV {uv_txt} : crème solaire SPF adapté si UV ≥ 3, renouvellement toutes les 2h.
- Pollen {pollen_txt} : conseils pratiques si alerte active.
- Éclairage : si départ avant {lever_str} ou arrivée après {coucher_str}.
- Wind chill : {ressenti_txt} — alerte si <5°C.
Note : intègre ces données naturellement dans ton texte, ne les recopie pas entre guillemets.

---

## ⚡ Plan de course

Décompose en phases chronologiques avec les kilomètres et heures estimées.
Pour chaque phase : niveau d'effort, raison précise (vent/pente/chaleur/fatigue cumulée), conseil tactique concret.
Pour chaque ascension : heure d'attaque, stratégie de montée (gestion de l'effort sur les passages à X%), gestion de la descente.

IMPORTANT — Le vent dans le plan de course (le coureur est SEUL, pas de roue ni de peloton) :
Données vent : {vent_txt} (rafales max {vent_max} km/h)
→ Vent de face sur un segment : baisser la cadence, position aéro, ne pas se battre inutilement
→ Vent de dos : récupérer ou relancer selon la fatigue du moment
→ Ne pas suggérer de chercher une roue ou un abri derrière quelqu'un — il est seul
→ Ces infos s'intègrent naturellement dans les phases, pas en liste séparée

Identifie les 2 meilleurs moments pour "appuyer" et les 2 moments où il doit absolument "lever le pied".
Donne de la couleur : une phrase de ressenti ou d'ambiance par phase (météo, paysage, fatigue probable à ce stade).

---

## 🍌 Ravitaillement

**Eau** : {eau_total} L — {eau_conseil}
{"⚠️ Électrolytes obligatoires (chaleur)." if t_max is not None and t_max >= 25 else ""}
{eau_txt}
Si points d'eau disponibles : stratégie de remplissage aux km précis.

**Énergie** : {carbs_total} g de glucides sur {dh}h{dm:02d}
Option A : {nb_barres} barres énergétiques (40g gl. chacune)
Option B : {nb_gels} gels (25g) + 1-2 bananes pour l'apport solide
Conseil : solide en 1ère moitié, gel/liquide en 2ème moitié.
Rythme : 1 prise toutes les 30 min dès la 1ère heure.

---

## ✅ Les 3 priorités de cette sortie

Exactement 3 points, les plus importants pour CETTE sortie spécifique.
Chacun doit être directement lié aux données fournies — pas de généralités.
Format : **[Thème]** — action concrète et chiffrée, avec le pourquoi en une demi-phrase.
Sois direct, presque brutal dans la formulation — c'est ce qu'un bon DS dirait vraiment.
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logger.error(f"Erreur Gemini : {e}")
        raise e

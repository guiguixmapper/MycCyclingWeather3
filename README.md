# 🚴 Vélo & Météo

> Analysez votre tracé GPX avant de partir. Météo en temps réel, cols UCI, profil interactif, points d'eau, UV, pollen et briefing IA personnalisé.

**→ [Voir l'application](https://mycyclingweather3.streamlit.app)**

---

## Ce que fait l'app

Importez un fichier GPX, choisissez votre date et heure de départ — l'app fait le reste.

### 🗺️ Carte interactive
- Tracé GPX avec checkpoints météo colorés selon la température
- Flèches de direction du vent au survol
- Cols et sommets identifiés via OpenStreetMap
- Points d'eau (fontaines, sources, bornes) sur le parcours
- 3 fonds de carte : CartoDB Positron, OpenStreetMap, OpenTopoMap

### ⛰️ Profil & Cols
- Profil altimétrique interactif coloré par catégorie UCI
- Détection automatique des ascensions (algorithme slope-first)
- Catégorisation UCI : HC, 1ère, 2ème, 3ème, 4ème, NC
- Profil détaillé par montée avec intensité de pente segment par segment
- Estimation puissance (W) et fréquence cardiaque par ascension

### 🌤️ Météo
- Données Open-Meteo en temps réel ou archives pour dates passées
- Température, vent, rafales, probabilité de pluie par checkpoint
- Wind chill (formule NOAA) si temp ≤ 10°C et vent > 4.8 km/h
- Répartition du vent (% face / dos / côté) avec segments kilométriques
- Indice UV max du jour
- Alertes pollen : Graminées, Bouleau, Olivier, Aulne, Armoise, Ambroisie

### 🏔️ Ascensions
- Tableau complet avec D+, longueur, pente moy/max, altitude sommet
- Heure d'arrivée estimée au sommet
- Puissance estimée et zone d'entraînement par col

### 📋 Détail météo
- Tableau horaire complet : ciel, temp, ressenti, pluie, vent, rafales, direction, effet

### 🤖 Coach IA (Google Gemini)
- Briefing complet personnalisé : résumé, météo & équipement, plan de course, ravitaillement
- Conseils nutrition et hydratation calculés selon la durée et la température
- Gestion du vent adaptée au coureur solo
- Ton humain : un ami, un grand frère de route, un coach qui connaît la souffrance du vélo

---

## Installation locale

### Prérequis
- Python 3.10+
- Un fichier GPX

### Installation

```bash
git clone https://github.com/ton-username/ton-repo.git
cd ton-repo
pip install -r requirements.txt
streamlit run app.py
```

### Configuration (optionnel)

Créer `.streamlit/config.toml` pour forcer le thème clair :

```toml
[theme]
base = "light"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f9fafb"
textColor = "#111827"
font = "sans serif"
```

---

## Utilisation

1. **Importer un fichier GPX** dans la sidebar
2. **Choisir la date et l'heure de départ**
3. **Régler la vitesse moyenne** sur le plat
4. **Configurer la physiologie** : mode Puissance (FTP) ou Fréquence Cardiaque
5. **Explorer les onglets** : Carte, Profil & Cols, Météo, Ascensions, Détail
6. **Activer le Coach IA** avec une clé API Gemini (gratuite sur [aistudio.google.com](https://aistudio.google.com))
7. **Télécharger le Roadbook** HTML/PDF depuis la sidebar

---

## Sources de données

| Donnée | Source | Cache |
|--------|--------|-------|
| Météo prévisions | [Open-Meteo](https://open-meteo.com) | 1h |
| Météo archives | [Open-Meteo Archive](https://open-meteo.com) | 1h |
| UV index | [Open-Meteo](https://open-meteo.com) | 1h |
| Pollen | [Open-Meteo Air Quality](https://open-meteo.com) | 1h |
| Cols & sommets | [OpenStreetMap / Overpass](https://overpass-api.de) | 24h |
| Points d'eau | [OpenStreetMap / Overpass](https://overpass-api.de) | 24h |
| Lever/coucher soleil | [Sunrise-Sunset.org](https://sunrise-sunset.org) | ∞ |
| Briefing IA | [Google Gemini 2.5 Flash](https://aistudio.google.com) | — |

Toutes les APIs météo et cartographiques utilisées sont **gratuites et sans clé** (sauf Gemini).

---

## Structure du projet

```
├── app.py              # Application principale Streamlit
├── climbing.py         # Détection et catégorisation des ascensions (slope-first)
├── weather.py          # Météo, UV, pollen, wind chill
├── overpass.py         # Cols OSM, points d'eau
├── map_builder.py      # Carte Folium interactive
├── gemini_coach.py     # Briefing IA via Google Gemini
├── requirements.txt    # Dépendances Python
└── .streamlit/
    └── config.toml     # Configuration thème (optionnel)
```

---

## Dépendances principales

```
streamlit
pandas
gpxpy
folium
streamlit-folium
plotly
requests
google-generativeai
```

---

## Limitations connues

- **Open-Meteo** : limite de requêtes sur le plan gratuit (429 géré avec retry automatique). En cas d'erreur, patienter 1-2 minutes et réessayer.
- **Overpass API** : les serveurs peuvent être lents ou indisponibles sur Streamlit Cloud. Le nommage des cols est optionnel.
- **Pollen** : données disponibles uniquement en Europe, pendant la saison pollinique.
- **Météo archives** : pour les dates passées, les données de précipitations sont en mm (pas en probabilité).

---

## Licence

MIT — libre d'utilisation, de modification et de distribution.

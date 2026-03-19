"""
map_builder.py — v3
====================
Carte Folium soignée pour l'app Vélo & Météo.

Calques :
    📍 Parcours   — tracé GPX + départ/arrivée
    🌤️ Météo      — checkpoints avec température colorée + popup complet
    🏔️ Ascensions — sommets UCI avec popup détaillé
    💧 Points d'eau — fontaines / sources / bornes avec type et popup

Design :
    - Tracé dégradé bleu électrique, épaisseur 5px
    - Icônes DivIcon custom : ronds colorés avec emoji, ombre portée
    - Popups avec mini-fiche HTML structurée
    - LayerControl stylé, calque Eau masqué par défaut
    - Tuile CartoDB Positron (fond clair, lisible)
"""

import folium
import math


# ==============================================================================
# HELPERS — ICÔNES
# ==============================================================================

def _rond(emoji: str, bg: str, size: int = 30, font: int = 14) -> str:
    """Icône ronde colorée avec emoji centré et ombre."""
    return (
        f'<div style="'
        f'background:{bg};color:white;border-radius:50%;'
        f'width:{size}px;height:{size}px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:{font}px;border:2px solid white;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.35);line-height:1;'
        f'">{emoji}</div>'
    )


def _badge(texte: str, bg: str) -> str:
    """Badge rectangulaire arrondi (pour la température)."""
    return (
        f'<div style="'
        f'background:{bg};color:white;border-radius:10px;'
        f'padding:3px 7px;font-size:11px;font-weight:700;'
        f'border:1.5px solid white;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.3);line-height:1.2;'
        f'white-space:nowrap;'
        f'">{texte}</div>'
    )


def _couleur_temp(t: float) -> str:
    if t < 5:   return "#5E5CE6"   # violet — très froid
    if t < 15:  return "#007AFF"   # bleu   — frais
    if t < 22:  return "#34C759"   # vert   — idéal
    if t < 30:  return "#FF9500"   # orange — chaud
    return              "#FF3B30"  # rouge  — très chaud


def _couleur_eau(type_eau: str) -> str:
    return {
        "fontaine": "#0ea5e9",   # bleu clair
        "source":   "#06b6d4",   # cyan
        "borne":    "#3b82f6",   # bleu
    }.get(type_eau, "#32ADE6")


COULEURS_CAT = {
    "🔴 HC":        "#ef4444",
    "🟠 1ère Cat.": "#f97316",
    "🟡 2ème Cat.": "#eab308",
    "🟢 3ème Cat.": "#22c55e",
    "🔵 4ème Cat.": "#3b82f6",
    "⚪ NC":        "#94a3b8",
}

EMOJI_EAU = {
    "fontaine": "⛲",
    "source":   "🌊",
    "borne":    "🚰",
    "eau":      "💧",
}


# ==============================================================================
# POPUPS
# ==============================================================================

def _popup_meteo(cp: dict, t: float) -> str:
    res = cp.get("ressenti")
    pp  = cp.get("pluie_pct")
    vv  = cp.get("vent_val", 0) or 0

    barre_pluie = ""
    if pp is not None:
        pc = "#1d4ed8" if pp >= 70 else "#2563eb" if pp >= 40 else "#60a5fa"
        barre_pluie = (
            f'<div style="margin:5px 0 2px;font-size:11px">🌧️ Pluie : <b>{pp}%</b></div>'
            f'<div style="background:#e2e8f0;border-radius:4px;height:5px;width:100%">'
            f'<div style="background:{pc};width:{pp}%;height:5px;border-radius:4px"></div></div>'
        )

    ressenti_line = (
        f'<span style="color:#6b7280;font-size:11px">&nbsp;(ressenti {res}°C)</span>'
        if res else ""
    )

    return (
        '<div style="font-family:-apple-system,sans-serif;font-size:12px;min-width:200px">'
        f'<div style="font-weight:700;font-size:13px;border-bottom:1px solid #e2e8f0;'
        f'padding-bottom:5px;margin-bottom:7px">'
        f'🕐 {cp["Heure"]} — Km {cp["Km"]}</div>'
        f'<div style="font-size:15px;margin-bottom:4px">'
        f'{cp.get("Ciel","—")} <b>{t}°C</b>{ressenti_line}</div>'
        f'{barre_pluie}'
        f'<div style="margin-top:7px;padding-top:6px;border-top:1px solid #f1f5f9;font-size:11px">'
        f'💨 <b>{vv} km/h</b> du {cp.get("Dir","—")} '
        f'— Rafales : {cp.get("rafales_val","—")} km/h<br>'
        f'🚴 Effet : <b>{cp.get("effet","—")}</b>'
        f'</div></div>'
    )


def _popup_col(asc: dict) -> str:
    nom = asc.get("Nom", "—")
    alt_osm = asc.get("Nom OSM alt")
    alt_line = (
        f'<div>⛰️ {asc["Alt. sommet"]}'
        + (f' · OSM : {alt_osm} m' if alt_osm else '')
        + '</div>'
    )
    temps_line = (
        f'<div style="margin-top:5px">⏱️ {asc.get("Temps col","—")} · arr. {asc.get("Arrivée sommet","—")}</div>'
        if asc.get("Temps col") else ""
    )
    return (
        '<div style="font-family:-apple-system,sans-serif;font-size:12px;min-width:190px">'
        f'<div style="font-weight:700;font-size:14px;margin-bottom:6px">'
        f'{"🏔️ "+nom+" — " if nom != "—" else "🏔️ "}{asc["Catégorie"]}</div>'
        f'<div>📏 {asc["Longueur"]} &nbsp;·&nbsp; D+ {asc["Dénivelé"]}</div>'
        f'<div>📐 {asc["Pente moy."]} moy. &nbsp;·&nbsp; {asc["Pente max"]} max</div>'
        f'{alt_line}{temps_line}'
        f'</div>'
    )


def _popup_eau(pt: dict) -> str:
    type_eau = pt.get("type", "eau")
    emoji    = EMOJI_EAU.get(type_eau, "💧")
    label    = type_eau.capitalize()
    nom      = pt.get("nom", "Point d'eau")
    return (
        '<div style="font-family:-apple-system,sans-serif;font-size:12px;min-width:150px">'
        f'<div style="font-weight:700;font-size:13px;margin-bottom:5px">'
        f'{emoji} {nom}</div>'
        f'<div style="color:#6b7280">{label} · eau potable</div>'
        f'</div>'
    )


# ==============================================================================
# CSS LAYER CONTROL
# ==============================================================================

CSS_LAYERS = """
<style>
.leaflet-control-layers {
    border-radius: 12px !important;
    border: none !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12) !important;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    overflow: hidden;
}
.leaflet-control-layers-expanded {
    padding: 10px 14px !important;
    min-width: 170px !important;
}
.leaflet-control-layers-expanded::before {
    content: "🗺️ Calques";
    display: block;
    font-weight: 700;
    font-size: 11px;
    color: #64748b;
    letter-spacing: .5px;
    text-transform: uppercase;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
}
.leaflet-control-layers label {
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    font-size: 13px !important;
    color: #1e293b !important;
    margin: 4px 0 !important;
    cursor: pointer !important;
}
</style>
"""


# ==============================================================================
# FONCTION PRINCIPALE
# ==============================================================================

def creer_carte(
    points_gpx: list,
    resultats:  list,
    ascensions: list,
    points_eau: list,
    tiles:      str = "CartoDB positron",
    attr:       str = None,
) -> folium.Map:
    """
    Construit la carte Folium complète.

    Args:
        points_gpx : liste de points gpxpy
        resultats  : checkpoints météo enrichis
        ascensions : liste de dicts ascensions (avec _lat_sommet etc.)
        points_eau : liste de dicts {"lat", "lon", "nom", "type"}
        tiles      : fond de carte Folium
        attr       : attributions (optionnel)

    Returns:
        folium.Map prête à afficher.
    """
    kwargs = dict(
        location=[points_gpx[0].latitude, points_gpx[0].longitude],
        zoom_start=11, tiles=tiles, scrollWheelZoom=True,
    )
    if attr:
        kwargs["attr"] = attr
    carte = folium.Map(**kwargs)

    # ── CALQUES ───────────────────────────────────────────────────────────────
    fg_trace = folium.FeatureGroup(name="📍 Parcours",    show=True)
    fg_meteo = folium.FeatureGroup(name="🌤️ Météo",      show=True)
    fg_cols  = folium.FeatureGroup(name="🏔️ Ascensions", show=True)
    fg_eau   = folium.FeatureGroup(name="💧 Points d'eau", show=True)

    # ── TRACÉ GPX ─────────────────────────────────────────────────────────────
    folium.PolyLine(
        [[p.latitude, p.longitude] for p in points_gpx],
        color="#2563eb", weight=5, opacity=0.88,
        tooltip="Parcours",
    ).add_to(fg_trace)

    # Départ
    folium.Marker(
        [points_gpx[0].latitude, points_gpx[0].longitude],
        tooltip=folium.Tooltip("🚦 Départ", sticky=True),
        icon=folium.DivIcon(html=_rond("▶", "#34C759", size=32, font=13),
                            icon_size=(32, 32), icon_anchor=(16, 16)),
    ).add_to(fg_trace)

    # Arrivée
    folium.Marker(
        [points_gpx[-1].latitude, points_gpx[-1].longitude],
        tooltip=folium.Tooltip("🏁 Arrivée", sticky=True),
        icon=folium.DivIcon(html=_rond("🏁", "#FF3B30", size=32, font=14),
                            icon_size=(32, 32), icon_anchor=(16, 16)),
    ).add_to(fg_trace)

    # ── MÉTÉO ─────────────────────────────────────────────────────────────────
    for cp in resultats:
        t = cp.get("temp_val")
        if t is None:
            continue
        coul = _couleur_temp(t)
        folium.Marker(
            [cp["lat"], cp["lon"]],
            popup=folium.Popup(_popup_meteo(cp, t), max_width=240),
            tooltip=folium.Tooltip(
                f"{cp['Heure']} · {cp.get('Ciel','')}{t}°C · 💨{cp.get('vent_val',0)} km/h",
                sticky=True,
            ),
            icon=folium.DivIcon(
                html=_badge(f"{t}°", coul),
                icon_size=(50, 24), icon_anchor=(25, 12),
            ),
        ).add_to(fg_meteo)

    # ── ASCENSIONS ────────────────────────────────────────────────────────────
    for asc in ascensions:
        lat_s = asc.get("_lat_sommet")
        lon_s = asc.get("_lon_sommet")
        if lat_s is None or lon_s is None:
            continue
        cat  = asc["Catégorie"]
        nom  = asc.get("Nom", "—")
        coul = COULEURS_CAT.get(cat, "#94a3b8")
        label = nom if nom != "—" else cat.split()[0]
        folium.Marker(
            [lat_s, lon_s],
            popup=folium.Popup(_popup_col(asc), max_width=230),
            tooltip=folium.Tooltip(f"▲ {label} — {asc['Alt. sommet']}", sticky=True),
            icon=folium.DivIcon(
                html=_rond("▲", coul, size=28, font=12),
                icon_size=(28, 28), icon_anchor=(14, 14),
            ),
        ).add_to(fg_cols)

    # ── POINTS D'EAU ─────────────────────────────────────────────────────────
    for pt in points_eau:
        type_eau = pt.get("type", "eau")
        coul     = _couleur_eau(type_eau)
        emoji    = EMOJI_EAU.get(type_eau, "💧")
        nom      = pt.get("nom", "Point d'eau")
        folium.Marker(
            [pt["lat"], pt["lon"]],
            popup=folium.Popup(_popup_eau(pt), max_width=200),
            tooltip=folium.Tooltip(f"{emoji} {nom}", sticky=True),
            icon=folium.DivIcon(
                html=_rond(emoji, coul, size=26, font=13),
                icon_size=(26, 26), icon_anchor=(13, 13),
            ),
        ).add_to(fg_eau)

    # ── ASSEMBLAGE ────────────────────────────────────────────────────────────
    for fg in [fg_trace, fg_meteo, fg_cols, fg_eau]:
        fg.add_to(carte)

    folium.LayerControl(collapsed=False, position="topright").add_to(carte)
    carte.get_root().html.add_child(folium.Element(CSS_LAYERS))

    return carte

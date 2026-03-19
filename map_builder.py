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
    "fontaine": "💧",
    "source":   "💧",
    "borne":    "💧",
    "eau":      "💧",
}


# ==============================================================================
# POPUPS
# ==============================================================================

def _fleche_vent(dir_deg, vitesse, effet) -> str:
    """
    Flèche SVG rotative indiquant la direction D'OÙ vient le vent,
    colorée selon la vitesse, avec label effet cycliste.
    """
    # Couleur selon vitesse
    if vitesse is None or vitesse == 0:
        coul = "#94a3b8"
    elif vitesse < 10:  coul = "#22c55e"
    elif vitesse < 25:  coul = "#eab308"
    elif vitesse < 40:  coul = "#f97316"
    else:               coul = "#ef4444"

    # La flèche pointe dans la direction où va le vent (dir_deg + 180 = d'où il vient → où il va)
    rotation = (dir_deg + 180) % 360 if dir_deg is not None else 0

    # Couleur de fond de l'effet
    effet_bg = {
        "⬇️ Face":     "#fee2e2",
        "⬆️ Dos":      "#dcfce7",
        "↙️ Côté (D)": "#fef9c3",
        "↘️ Côté (G)": "#fef9c3",
    }.get(effet, "#f1f5f9")
    effet_color = {
        "⬇️ Face":     "#dc2626",
        "⬆️ Dos":      "#16a34a",
        "↙️ Côté (D)": "#ca8a04",
        "↘️ Côté (G)": "#ca8a04",
    }.get(effet, "#64748b")

    svg = (
        f'<svg width="44" height="44" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">'
        f'  <circle cx="22" cy="22" r="20" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.5"/>'
        f'  <g transform="rotate({rotation}, 22, 22)">'
        f'    <polygon points="22,6 27,32 22,28 17,32" fill="{coul}" opacity="0.95"/>'
        f'    <circle cx="22" cy="22" r="3" fill="{coul}"/>'
        f'  </g>'
        f'</svg>'
    )

    vitesse_str = f"{int(vitesse)} km/h" if vitesse else "— km/h"
    effet_str   = effet if effet and effet != "—" else "—"

    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin-top:6px">'
        f'  {svg}'
        f'  <div>'
        f'    <div style="font-size:13px;font-weight:700;color:#1e293b">{vitesse_str}</div>'
        f'    <div style="font-size:10px;color:#64748b">rafales : {{}}</div>'
        f'    <div style="display:inline-block;margin-top:3px;padding:2px 7px;border-radius:10px;'
        f'         font-size:10px;font-weight:600;background:{effet_bg};color:{effet_color}">'
        f'      {effet_str}</div>'
        f'  </div>'
        f'</div>'
    )


def _popup_meteo(cp: dict, t: float) -> str:
    res    = cp.get("ressenti")
    pp     = cp.get("pluie_pct")
    vv     = cp.get("vent_val", 0) or 0
    rg     = cp.get("rafales_val", "—")
    dir_deg = cp.get("dir_deg")
    effet  = cp.get("effet", "—")

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

    fleche = _fleche_vent(dir_deg, vv, effet).format(rg if rg else "—")

    return (
        '<div style="font-family:-apple-system,sans-serif;font-size:12px;min-width:210px">'
        f'<div style="font-weight:700;font-size:13px;border-bottom:1px solid #e2e8f0;'
        f'padding-bottom:5px;margin-bottom:7px">'
        f'🕐 {cp["Heure"]} — Km {cp["Km"]}</div>'
        f'<div style="font-size:15px;margin-bottom:4px">'
        f'{cp.get("Ciel","—")} <b>{t}°C</b>{ressenti_line}</div>'
        f'{barre_pluie}'
        f'<div style="padding-top:6px;border-top:1px solid #f1f5f9">'
        f'  <div style="font-size:11px;color:#64748b;margin-bottom:2px">'
        f'    💨 Vent du {cp.get("Dir","—")}</div>'
        f'  {fleche}'
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
        dir_deg = cp.get("dir_deg")
        vv      = cp.get("vent_val", 0) or 0
        effet   = cp.get("effet", "—")

        # Couleur flèche selon vitesse
        if vv == 0:       fc = "#94a3b8"
        elif vv < 10:     fc = "#22c55e"
        elif vv < 25:     fc = "#eab308"
        elif vv < 40:     fc = "#f97316"
        else:             fc = "#ef4444"

        # Couleur badge effet
        effet_bg  = {"⬇️ Face":"#fee2e2","⬆️ Dos":"#dcfce7","↙️ Côté (D)":"#fef9c3","↘️ Côté (G)":"#fef9c3"}.get(effet,"#f1f5f9")
        effet_col = {"⬇️ Face":"#dc2626","⬆️ Dos":"#16a34a","↙️ Côté (D)":"#ca8a04","↘️ Côté (G)":"#ca8a04"}.get(effet,"#64748b")

        rotation = (dir_deg + 180) % 360 if dir_deg is not None else 0

        svg_arrow = (
            f'<svg width="32" height="32" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0">'
            f'<circle cx="22" cy="22" r="20" fill="white" stroke="#e2e8f0" stroke-width="1.5"/>'
            f'<g transform="rotate({rotation},22,22)">'
            f'<polygon points="22,6 27,32 22,28 17,32" fill="{fc}"/>'
            f'<circle cx="22" cy="22" r="3" fill="{fc}"/>'
            f'</g></svg>'
        )

        tooltip_html = (
            f'<div style="font-family:-apple-system,sans-serif;font-size:12px;'
            f'background:white;padding:8px 10px;border-radius:8px;'
            f'box-shadow:0 2px 8px rgba(0,0,0,0.15);min-width:190px">'
            f'<div style="font-weight:700;margin-bottom:5px">🕐 {cp["Heure"]} · Km {cp["Km"]}</div>'
            f'<div style="margin-bottom:5px">{cp.get("Ciel","—")} <b>{t}°C</b></div>'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'  {svg_arrow}'
            f'  <div>'
            f'    <div style="font-size:12px;font-weight:600">{vv} km/h du {cp.get("Dir","—")}</div>'
            f'    <div style="display:inline-block;margin-top:2px;padding:1px 6px;border-radius:8px;'
            f'         font-size:10px;font-weight:600;background:{effet_bg};color:{effet_col}">'
            f'      {effet}</div>'
            f'  </div>'
            f'</div></div>'
        )

        folium.Marker(
            [cp["lat"], cp["lon"]],
            popup=folium.Popup(_popup_meteo(cp, t), max_width=240),
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
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

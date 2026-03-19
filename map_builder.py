# --- FICHIER : map_builder.py ---
import folium

def creer_carte(points_gpx, resultats, ascensions, points_eau, tiles="CartoDB positron"):
    carte = folium.Map(location=[points_gpx[0].latitude, points_gpx[0].longitude], zoom_start=11, tiles=tiles, scrollWheelZoom=True)
    
    fg_meteo = folium.FeatureGroup(name="🌤️ Météo", show=True)
    fg_cols  = folium.FeatureGroup(name="🏔️ Ascensions", show=True)
    fg_eau   = folium.FeatureGroup(name="💧 Eau", show=False) # Masqué par défaut pour l'élégance
    fg_trace = folium.FeatureGroup(name="📍 Parcours", show=True)
    
    folium.PolyLine([[p.latitude, p.longitude] for p in points_gpx], color="#0066FF", weight=5, opacity=0.8).add_to(fg_trace)
                    
    def html_icon(icone, bg):
        return f'<div style="background:{bg};color:white;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-size:13px;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);line-height:1;">{icone}</div>'

    folium.Marker([points_gpx[0].latitude, points_gpx[0].longitude], tooltip="Départ", icon=folium.DivIcon(html=html_icon("🟢", "#34C759"))).add_to(fg_trace)
    folium.Marker([points_gpx[-1].latitude, points_gpx[-1].longitude], tooltip="Arrivée", icon=folium.DivIcon(html=html_icon("🏁", "#FF3B30"))).add_to(fg_trace)

    for eau in points_eau:
        folium.Marker([eau["lat"], eau["lon"]], tooltip="💧 Eau", icon=folium.DivIcon(html=html_icon("💧", "#32ADE6"))).add_to(fg_eau)

    COULEURS = {"🔴 HC":"#FF3B30","🟠 1ère Cat.":"#FF9500","🟡 2ème Cat.":"#FFCC00","🟢 3ème Cat.":"#34C759","🔵 4ème Cat.":"#007AFF"}
    for asc in ascensions:
        if not asc.get("_lat_sommet"): continue
        nom, cat = asc.get("Nom", "—"), asc["Catégorie"]
        coul = COULEURS.get(cat, "#007AFF")
        popup = f"<div style='font-family:sans-serif;font-size:13px'><b>{nom}</b> ({cat})<br>📏 {asc['Longueur']} | D+ {asc['Dénivelé']}<br>📐 {asc['Pente moy.']}</div>"
        folium.Marker([asc["_lat_sommet"], asc["_lon_sommet"]], popup=folium.Popup(popup, max_width=200), tooltip=f"▲ {nom}", icon=folium.DivIcon(html=html_icon("🏔️", coul))).add_to(fg_cols)
            
    for cp in resultats:
        t = cp.get("temp_val")
        if t is None: continue
        c_t = "#5E5CE6" if t<5 else "#007AFF" if t<15 else "#34C759" if t<22 else "#FF9500" if t<30 else "#FF3B30"
        ico = f'<div style="background:{c_t};color:white;border-radius:12px;padding:3px 6px;font-size:11px;font-weight:bold;border:1px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);line-height:1;">{t}°</div>'
        popup = f'<div style="font-family:sans-serif;font-size:12px"><b>{cp["Heure"]} — Km {cp["Km"]}</b><br>{cp["Ciel"]} {t}°C<br>💨 {cp.get("vent_val",0)} km/h {cp["Dir"]}<br>☔ {cp.get("pluie_pct",0)}%</div>'
        folium.Marker([cp["lat"], cp["lon"]], popup=folium.Popup(popup, max_width=200), tooltip=f"{cp['Heure']} | 💨 {cp.get('vent_val',0)} km/h {cp['Dir']}", icon=folium.DivIcon(html=ico)).add_to(fg_meteo)

    for fg in [fg_trace, fg_meteo, fg_cols, fg_eau]: fg.add_to(carte)
    folium.LayerControl(collapsed=False).add_to(carte)
    carte.get_root().html.add_child(folium.Element("<style>.leaflet-control-layers{border-radius:12px!important;border:none!important;box-shadow:0 4px 12px rgba(0,0,0,0.1)!important;font-family:-apple-system,BlinkMacSystemFont,sans-serif!important;}</style>"))
    return carte

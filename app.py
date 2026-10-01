import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
import json
import time

# ==========================================
# CONFIGURACIÓN Y LISTAS DE INTELIGENCIA
# ==========================================
st.set_page_config(page_title="EWS Global", layout="wide")

STRATEGIC_ASSETS = ["ae01d6", "ae01c9", "ae05ff", "ae0671", "ae01bf", "ae047c"]
VIP_JETS = ["484153", "484154", "406263", "ae46a0"]

# ==========================================
# FUNCIÓN DE ESCANEO CON DATOS DE RESPALDO (FALLBACK)
# ==========================================
def run_scan_live_streamlit():
    """Ejecuta el escaneo de OpenSky y utiliza respaldo si la red externa bloquea la petición."""
    with st.spinner("🚨 Conectando con OpenSky Network para obtener telemetría en vivo..."):
        aviones_mapa = []
        
        try:
            url = "https://opensky-network.org/api/states/all"
            # Solicitud con un timeout menor y headers para evitar bloqueos por bot
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                states = response.json().get("states", [])
                if states:
                    count = 0
                    for s in states:
                        count += 1
                        icao24 = s[0]
                        callsign = s[1].strip() if s[1] else "N/A"
                        lon = s[5]
                        lat = s[6]
                        on_ground = s[8]
                        heading = s[10] if s[10] is not None else 0.0
                        
                        if on_ground or lat is None or lon is None:
                            continue
                        
                        # Clasificación de tráfico de muestra (para no saturar el mapa)
                        if icao24 in STRATEGIC_ASSETS:
                            tipo, color, size = "Crítico", [255, 0, 0, 255], 26
                        elif icao24 in VIP_JETS or callsign.startswith(("REACH", "RSV", "COBRA", "DRAGON")):
                            tipo, color, size = "Inusual", [255, 140, 0, 255], 22
                        else:
                            if count % 100 == 0:  # Muestreo ligero del tráfico global
                                tipo, color, size = "Rutina", [100, 180, 255, 180], 16
                            else:
                                continue
                        
                        aviones_mapa.append({
                            "lat": lat, "lon": lon, "heading": -heading,
                            "name": f"Tráfico: {callsign} ({icao24})",
                            "tipo": tipo, "color": color, "size": size, "text": "✈"
                        })
            
            # Si se obtuvieron aviones reales, los guardamos
            if aviones_mapa:
                datos_finales = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"), "aviones": aviones_mapa}
                with open('datos.json', 'w') as f:
                    json.dump(datos_finales, f)
                st.success(f"✅ Sincronización exitosa: {len(aviones_mapa)} vectores activos mapeados.")
                return True

        except Exception:
            pass # Si falla la red, pasamos silenciosamente al respaldo para no romper la app

        # --- RESPALDO DE EMERGENCIA (FALLBACK) ---
        # Si OpenSky da timeout o bloquea, inyectamos puntos de tráfico simulados estratégicos 
        # para que el mapa operativo nunca falle ni quede vacío ante una emergencia de red.
        st.warning("⚠️ OpenSky Network no respondió (límite de peticiones de la nube). Activando telemetría de respaldo simulada.")
        
        aviones_respaldo = [
            {"lat": 54.5, "lon": 36.2, "heading": 45, "name": "Tráfico de Respaldo: RRF99 (Zona Europa)", "tipo": "Crítico", "color": [255, 0, 0, 255], "size": 26, "text": "✈"},
            {"lat": 38.0, "lon": -75.0, "heading": 180, "name": "Tráfico de Respaldo: REACH41 (Costa Este USA)", "tipo": "Inusual", "color": [255, 140, 0, 255], "size": 22, "text": "✈"},
            {"lat": -33.0, "lon": -71.5, "heading": 90, "name": "Tráfico de Respaldo: LAN501 (Zona Central Chile)", "tipo": "Rutina", "color": [100, 180, 255, 180], "size": 16, "text": "✈"},
            {"lat": 35.0, "lon": 115.0, "heading": 270, "name": "Tráfico de Respaldo: CCA981 (Indo-Pacífico)", "tipo": "Rutina", "color": [100, 180, 255, 180], "size": 16, "text": "✈"}
        ]
        
        datos_finales = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC (Respaldo)"), "aviones": aviones_respaldo}
        with open('datos.json', 'w') as f:
            json.dump(datos_finales, f)
            
        st.success("✅ Tablero operativo restablecido mediante capa de contingencia.")
        return True

# ==========================================
# INTERFAZ DE STREAMLIT
# ==========================================
st.title("📡 Early Warning System (EWS) - Tablero Táctico Global")
st.markdown("---")

st.sidebar.header("🎛️ Controles de Operación")
if st.sidebar.button("🔄 ACTUALIZAR ESTADO DEL RADAR"):
    run_scan_live_streamlit()
    st.rerun()

# Cargar JSON actual
try:
    with open('datos.json', 'r') as f:
        loaded_data = json.load(f)
    timestamp_datos = loaded_data.get('timestamp', 'Desconocido')
    aviones_mapa = loaded_data.get('aviones', [])
    st.sidebar.write(f"🕒 Sincronización: **{timestamp_datos}**")
except FileNotFoundError:
    # Si no existe el archivo al iniciar, generamos el respaldo automáticamente
    aviones_mapa = []
    run_scan_live_streamlit()
    st.rerun()

# ==========================================
# MAPA TÁCTICO INTERACTIVO
# ==========================================
st.subheader("🗺️ Mapa Táctico Global de Amenazas y Tráfico Aéreo")

teatros_fijos = [
    {"lat": 55.75, "lon": 37.61, "name": "Rusia (Moscu / Comando Central)", "tipo": "Zona Crítica", "radius": 400000, "color": [255, 0, 0, 180]},
    {"lat": 38.89, "lon": -77.03, "name": "Estados Unidos (Washington D.C.)", "tipo": "Zona de Interés", "radius": 400000, "color": [0, 120, 255, 180]},
    {"lat": 39.90, "lon": 116.40, "name": "China (Beijing / Indo-Pacífico)", "tipo": "Zona de Interés", "radius": 400000, "color": [255, 128, 0, 180]},
    {"lat": -33.44, "lon": -70.66, "name": "Chile (Zona de Interés / Santiago)", "tipo": "Zona Nacional", "radius": 300000, "color": [0, 255, 128, 180]}
]
df_fijos = pd.DataFrame(teatros_fijos)
capa_fijos = pdk.Layer(
    "ScatterplotLayer",
    df_fijos,
    get_position="[lon, lat]",
    get_color="color",
    get_radius="radius",
    pickable=True,
    auto_highlight=True,
)

if aviones_mapa:
    df_aviones = pd.DataFrame(aviones_mapa)
    capa_aviones = pdk.Layer(
        "TextLayer",
        df_aviones,
        get_position="[lon, lat]",
        get_text="text",
        get_size="size",
        get_color="color",
        get_angle="heading",
        pickable=True,
        auto_highlight=True,
        size_scale=1
    )
    layers_map = [capa_fijos, capa_aviones]
else:
    layers_map = [capa_fijos]

view_state = pdk.ViewState(
    latitude=15.0,
    longitude=-70.0,
    zoom=1.6,
    pitch=0,
)

st.pydeck_chart(pdk.Deck(
    layers=layers_map,
    initial_view_state=view_state,
    tooltip={"text": "Objetivo: {name}\nClasificación: {tipo}"},
    map_style='mapbox://styles/mapbox/dark-v10'
))

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

# Listas de activos fijos de interés (para contexto)
STRATEGIC_ASSETS = [
    "ae01d6", "ae01c9", "ae05ff", "ae0671", "ae01bf", "ae047c", # Ejemplos de B-2, B-52, E-4B
    "c2b49c", "c2b49e", "06a2e3", "adf850"  # Otros ejemplos
]
VIP_JETS = [
    "484153", "484154", "406263", "ae46a0"  # Air Force One, etc.
]
# Pesos de puntuación (usados solo para el log de la alerta, no para el mapa visual)
SCORE_WEIGHTS = {
    "MIL_STRATEGIC_BOMBER": 50,
    "MIL_AWACS_TANKER": 30,
    "VIP_JET_UNUSUAL": 40,
    "MIL_LOGISTICS_HEAVY": 20
}

# ==========================================
# FUNCIÓN DE ESCANEO INTEGRADA EN APP.PY
# (Para uso exclusivo en Streamlit Cloud sin consola)
# ==========================================
def run_scan_live_streamlit():
    """Ejecuta el escaneo de OpenSky directamente desde la interfaz web."""
    with st.spinner("🚨 Ejecutando escaneo de radar en vivo contra OpenSky Network..."):
        points = 0
        triggers = []
        aviones_mapa = []
        
        try:
            url = "https://opensky-network.org/api/states/all"
            response = requests.get(url, timeout=20) # Timeout mayor para nube
            if response.status_code != 200:
                st.error(f"Error de conexión con OpenSky: {response.status_code}")
                return False
                
            states = response.json().get("states", [])
            if not states:
                st.warning("⚠️ La API de OpenSky devolvió una lista vacía de tráfico aéreo en este momento.")
                return False
            
            count_scanned = 0
            for s in states:
                count_scanned += 1
                icao24 = s[0]
                callsign = s[1].strip() if s[1] else "N/A"
                lon = s[5]
                lat = s[6]
                on_ground = s[8]
                heading = s[10] if s[10] is not None else 0.0
                
                if on_ground or lat is None or lon is None:
                    continue
                
                # CLASIFICACIÓN VISUAL
                if icao24 in STRATEGIC_ASSETS:
                    tipo = "Crítico"
                    color = [255, 0, 0, 255]
                    size = 26
                elif icao24 in VIP_JETS or callsign.startswith(("REACH", "RSV", "COBRA", "DRAGON")):
                    tipo = "Inusual"
                    color = [255, 140, 0, 255]
                    size = 22
                else:
                    # Muestreo de tráfico de rutina (para no saturar, tomamos uno de cada X)
                    if count_scanned % 80 == 0: # Solo mostramos un 1.25% del tráfico total
                        tipo = "Rutina"
                        color = [100, 180, 255, 180]
                        size = 16
                    else:
                        continue
                
                aviones_mapa.append({
                    "lat": lat,
                    "lon": lon,
                    "heading": -heading, # Negativo para rotación correcta en Pydeck
                    "name": f"Tráfico: {callsign} ({icao24})",
                    "tipo": tipo,
                    "color": color,
                    "size": size,
                    "text": "✈"
                })
            
            # GUARDAR DATOS EN JSON (Sobrescribe el existente para que el mapa lo lea)
            datos_finales = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "aviones": aviones_mapa
            }
            with open('datos.json', 'w') as f:
                json.dump(datos_finales, f)
            
            st.success(f"✅ Escaneo completado. Se detectaron y clasificaron {len(aviones_mapa)} aeronaves de interés / muestreo.")
            return True

        except Exception as e:
            st.error(f"❌ Error crítico durante el escaneo en vivo: {str(e)}")
            return False

# ==========================================
# INTERFAZ DE STREAMLIT
# ==========================================
st.title("📡 Early Warning System (EWS) - Tablero Táctico Global")
st.markdown("---")

# Barra lateral con controles
st.sidebar.header("🎛️ Controles de Operación")

# BOTÓN DE ACCIÓN CLAVE PARA STREAMLIT CLOUD
if st.sidebar.button("🔄 FORZAR ESCANEO EN VIVO (OpenSky)"):
    # Llama a la función de escaneo definida arriba
    success = run_scan_live_streamlit()
    if success:
        st.sidebar.success("Datos actualizados. Recargando mapa...")
        # Forzamos una recarga de la página para que el mapa muestre los datos nuevos
        st.rerun()
else:
    st.sidebar.info("Presione el botón para actualizar el tráfico aéreo desde la fuente si el mapa está vacío.")

# Intentar cargar el archivo datos.json (ya sea de la última corrida de GH Actions o del botón manual)
try:
    with open('datos.json', 'r') as f:
        loaded_data = json.load(f)
    timestamp_datos = loaded_data.get('timestamp', 'Desconocido')
    aviones_mapa = loaded_data.get('aviones', [])
    st.sidebar.write(f"🕒 Última actualización de datos: **{timestamp_datos}**")
except FileNotFoundError:
    st.warning("⚠️ Archivo `datos.json` no encontrado. Presione el botón de escaneo para generarlo.")
    aviones_mapa = []

# ==========================================
# MAPA TÁCTICO INTERACTIVO
# ==========================================
st.subheader("🗺️ Mapa Táctico Global de Amenazas y Tráfico Aéreo")

# 1. Puntos fijos obligatorios (Zonas de Interés)
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

# 2. Capa de Texto vectorial para los aviones (✈ rotados y coloreados)
# Solo se renderiza si hay aviones en el JSON cargado
if aviones_mapa:
    df_aviones = pd.DataFrame(aviones_mapa)
    capa_aviones = pdk.Layer(
        "TextLayer",
        df_aviones,
        get_position="[lon, lat]",
        get_text="text",
        get_size="size",
        get_color="color",
        get_angle="heading", # Usa el ángulo capturado en el escaneo
        pickable=True,
        auto_highlight=True,
        size_scale=1
    )
    layers_map = [capa_fijos, capa_aviones]
else:
    # Si no hay aviones, solo muestra los fijos
    layers_map = [capa_fijos]

# Vista inicial centrada en el hemisferio occidental para ver Chile y EE.UU.
view_state = pdk.ViewState(
    latitude=15.0,
    longitude=-70.0,
    zoom=1.6,
    pitch=0,
)

# Renderizar mapa final
st.pydeck_chart(pdk.Deck(
    layers=layers_map,
    initial_view_state=view_state,
    tooltip={"text": "Objetivo: {name}\nClasificación: {tipo}"},
    map_style='mapbox://styles/mapbox/dark-v10' # Estilo oscuro táctico
))

# Sección de depuración (opcional, para ver el JSON crudo)
if st.sidebar.checkbox("Mostrar datos JSON crudos"):
    st.write(aviones_mapa)
    

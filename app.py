import streamlit as st
import pandas as pd
import pydeck as pdk
import json

# ==========================================
# CONFIGURACIÓN DE LA INTERFAZ
# ==========================================
st.set_page_config(page_title="EWS Global - Tablero Táctico", layout="wide")

st.title("📡 Early Warning System (EWS) - Tablero Táctico Global")
st.markdown("---")

# ==========================================
# CARGA DE DATOS AUTOMÁTICA (DESDE EL JSON)
# ==========================================
try:
    with open('datos.json', 'r') as f:
        loaded_data = json.load(f)
    
    timestamp_datos = loaded_data.get('timestamp', 'Desconocido')
    aviones_mapa = loaded_data.get('aviones', [])
    puntuacion_actual = loaded_data.get('score', 0)
    defcon_nivel = loaded_data.get('defcon', 5)
    triggers_activos = loaded_data.get('triggers', [])
    
except FileNotFoundError:
    timestamp_datos = "Sin datos"
    aviones_mapa = []
    puntuacion_actual = 0
    defcon_nivel = 5
    triggers_activos = ["Esperando el primer ciclo de escaneo del sistema..."]

# ==========================================
# PANEL SUPERIOR DE MONITOREO (DEFCON & MÉTRICAS)
# ==========================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    color_defcon = "🟢 DEFCON 5" if defcon_nivel >= 5 else ("🟡 DEFCON 3-4" if defcon_nivel >= 3 else "🔴 DEFCON 1-2")
    st.metric(label="Estado de Alerta (DEFCON)", value=color_defcon)

with col2:
    st.metric(label="Puntuación de Amenaza", value=f"{puntuacion_actual} pts")

with col3:
    st.metric(label="Vectores Aéreos Activos", value=len(aviones_mapa))

with col4:
    st.metric(label="Sincronización", value=timestamp_datos)

st.markdown("---")

if triggers_activos:
    with st.expander("🚨 Ver Registros y Triggers de Inteligencia Activos", expanded=False):
        for trg in triggers_activos:
            st.markdown(f"- {trg}")

# ==========================================
# MAPA TÁCTICO GLOBAL
# ==========================================
st.subheader("🗺️ Mapa Táctico Global de Amenazas y Tráfico Aéreo")

# 1. Puntos fijos de interés (Rusia, EE. UU., China y Chile)
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

layers_map = [capa_fijos]

# 2. Capa de Iconos Gráficos (IconLayer) para los aviones con silueta real e imagen PNG
if aviones_mapa:
    # URL pública de un icono de avión limpio y transparente optimizado para mapas
    icon_url = "https://cdn-icons-png.flaticon.com/512/723/723915.png"
    
    icon_data_list = []
    for av in aviones_mapa:
        # Preparamos cada registro agregando la estructura de diccionario de icono que exige Pydeck
        item = av.copy()
        item["icon_data"] = {
            "url": icon_url,
            "width": 128,
            "height": 128,
            "anchorY": 64,
            "mask": True # Permite colorear dinámicamente el icono PNG según el color asignado en el monitor
        }
        icon_data_list.append(item)

    df_aviones = pd.DataFrame(icon_data_list)
    
    capa_aviones = pdk.Layer(
        "IconLayer",
        df_aviones,
        get_position="[lon, lat]",
        get_icon="icon_data",
        get_size="size",
        get_color="color",
        get_angle="heading",
        size_scale=0.8,
        pickable=True,
        auto_highlight=True,
    )
    layers_map.append(capa_aviones)

# Vista inicial centrada globalmente
view_state = pdk.ViewState(
    latitude=15.0,
    longitude=0.0,
    zoom=1.5,
    pitch=0,
)

# Renderizar mapa limpio
st.pydeck_chart(pdk.Deck(
    layers=layers_map,
    initial_view_state=view_state,
    tooltip={"text": "Objetivo: {name}\nClasificación: {tipo}"}
))

import streamlit as st
import json
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Radar OSINT & EWS", layout="wide")

st.title("🌐 Radar OSINT / Early Warning System (EWS)")
st.markdown("Monitor de tensiones geopolíticas y predicción estratégica impulsada por IA.")

# Cargar los datos más recientes generados por monitor.py
try:
    with open("datos.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        current_defcon = data.get("defcon", 5)
        total_score = data.get("score", 0)
        triggers = data.get("triggers", [])
        timestamp = data.get("timestamp", "Desconocido")
        aviones_mapa = data.get("aviones_mapa", [])
except Exception:
    current_defcon = 5
    total_score = 0
    triggers = ["Esperando primer ciclo de ejecución..."]
    timestamp = "N/A"
    aviones_mapa = []

# Panel Superior de Métricas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Nivel DEFCON Actual", value=f"Nivel {current_defcon}")
with col2:
    st.metric(label="Puntaje de Tensión (Score)", value=f"{total_score} pts")
with col3:
    st.metric(label="Última Actualización (UTC)", value=timestamp)

st.markdown("---")

# Sección de Alertas y Vectores
st.subheader("🚨 Radar de Eventos y Doble Factor Confirmados")
if triggers:
    for t in triggers:
        if "CRÍTICO" in t or "CONVERGENCIA" in t:
            st.error(t)
        elif "ADVERTENCIA" in t or "VIP" in t:
            st.warning(t)
        else:
            st.info(t)
else:
    st.success("Sistema en régimen de rutina. Sin anomalías detectadas.")

st.markdown("---")

# ==========================================
# MAPA TÁCTICO INTERACTIVO (Estilo EWS Optimizado)
# ==========================================
st.subheader("🗺️ Mapa Táctico Global de Amenazas y Tráfico Aéreo")

# 1. Puntos fijos obligatorios (Zonas de Interés y Teatros Estratégicos)
teatros_fijos = [
    {"lat": 55.75, "lon": 37.61, "name": "Rusia (Moscu / Comando Central)", "tipo": "Zona Crítica", "radius": 400000, "color": [255, 0, 0, 180]},
    {"lat": 38.89, "lon": -77.03, "name": "Estados Unidos (Washington D.C.)", "tipo": "Zona de Interés", "radius": 400000, "color": [0, 120, 255, 180]},
    {"lat": 39.90, "lon": 116.40, "name": "China (Beijing / Indo-Pacífico)", "tipo": "Zona de Interés", "radius": 400000, "color": [255, 128, 0, 180]},
    {"lat": -33.44, "lon": -70.66, "name": "Chile (Zona de Interés / Santiago)", "tipo": "Zona Nacional", "radius": 300000, "color": [0, 255, 128, 180]}
]

df_fijos = pd.DataFrame(teatros_fijos)

# Capa para los círculos de las potencias y Chile
capa_fijos = pdk.Layer(
    "ScatterplotLayer",
    df_fijos,
    get_position="[lon, lat]",
    get_color="color",
    get_radius="radius",
    pickable=True,
    auto_highlight=True,
)

# 2. Procesamiento de aviones utilizando los colores y tipos definidos en el JSON
aviones_procesados = []
for av in aviones_mapa:
    tipo = av.get("tipo", "Rutina")
    color = av.get("color", [100, 180, 255, 120]) # Valor por defecto si no viene
    
    # Asignar tamaño dinámico según el nivel de alerta
    if tipo == "Crítico":
        size = 40000
    elif tipo == "Inusual":
        size = 30000
    else:
        size = 12000

    aviones_procesados.append({
        "lat": av["lat"],
        "lon": av["lon"],
        "name": av["name"],
        "tipo": tipo,
        "color": color,
        "radius": size
    })

df_aviones = pd.DataFrame(aviones_procesados)

# Capa de dispersión dinámica para los aviones
capa_aviones = pdk.Layer(
    "ScatterplotLayer",
    df_aviones,
    get_position="[lon, lat]",
    get_color="color",
    get_radius="radius",
    pickable=True,
    auto_highlight=True,
)

# Vista inicial centrada globalmente incluyendo los teatros clave y Chile
view_state = pdk.ViewState(
    latitude=15.0,
    longitude=0.0,
    zoom=1.4,
    pitch=0,
)

# Renderizar mapa combinando teatros fijos y tráfico aéreo clasificado
st.pydeck_chart(pdk.Deck(
    layers=[capa_fijos, capa_aviones],
    initial_view_state=view_state,
    tooltip={"text": "Objetivo: {name}\nClasificación: {tipo}"}
))

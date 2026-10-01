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
# MAPA TÁCTICO INTERACTIVO (Estilo EWS)
# ==========================================
st.subheader("🗺️ Mapa Táctico Global de Amenazas y Tráfico Aéreo")

# Coordenadas base de los teatros de operaciones y zonas de interés actualizadas
teatros_base = [
    {"lat": 55.75, "lon": 37.61, "name": "Rusia (Moscu / Comando Central)", "tipo": "Crítico"},
    {"lat": 38.89, "lon": -77.03, "name": "Estados Unidos (Washington D.C.)", "tipo": "Monitoreo"},
    {"lat": 39.90, "lon": 116.40, "name": "China (Beijing / Indo-Pacífico)", "tipo": "Observación"},
    {"lat": -33.44, "lon": -70.66, "name": "Chile (Zona de Interés / Santiago)", "tipo": "Nacional"}
]

# Fusionar teatros base con aviones activos detectados en tiempo real
puntos_totales = teatros_base + aviones_mapa
data_mapa = pd.DataFrame(puntos_totales)

# Capa visual interactiva con Pydeck
capa_mapa = pdk.Layer(
    "ScatterplotLayer",
    data_mapa,
    get_position="[lon, lat]",
    get_color="[200, 30, 0, 180]",
    get_radius=250000, # Radio de cobertura visual en metros
    pickable=True,
    auto_highlight=True,
)

# Vista inicial centrada a nivel global
view_state = pdk.ViewState(
    latitude=15.0,
    longitude=0.0,
    zoom=1.2,
    pitch=0,
)

st.pydeck_chart(pdk.Deck(
    layers=[capa_mapa],
    initial_view_state=view_state,
    tooltip={"text": "Ubicación/Objetivo: {name}\nTipo: {tipo}"}
))

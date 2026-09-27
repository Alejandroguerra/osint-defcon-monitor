import streamlit as st
import json
import pandas as pd
import os

st.set_page_config(page_title="Radar OSINT Global", page_icon="🌍", layout="wide")

st.title("🌍 Sistema de Alertas Global OSINT")
st.markdown("Monitor de tensiones geopolíticas y predicción estratégica impulsada por IA.")
st.divider()

# 1. CARGAR DATOS
try:
    with open("datos.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {"defcon": 5, "score": 0, "triggers": ["Esperando datos..."], "timestamp": "Desconocido"}

historial_disponible = False
try:
    if os.path.exists("historial.csv"):
        df_historial = pd.read_csv("historial.csv")
        historial_disponible = len(df_historial) > 0
except Exception:
    pass

# ==========================================
# 2. CREACIÓN DE PESTAÑAS (TABS)
# ==========================================
tab_realtime, tab_predict = st.tabs(["📡 Alertas en Tiempo Real", "🧠 Análisis Predictivo (IA)"])

# --- PESTAÑA 1: ALERTAS REALES ---
with tab_realtime:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Estado de Alerta Actual")
        colores_defcon = {1: "🔴 CRÍTICO", 2: "🟠 ESCALADA", 3: "🟡 PREVENCIÓN", 4: "🔵 MONITOREO", 5: "🟢 RUTINA"}
        
        st.metric(label="Nivel DEFCON", value=f"Nivel {data['defcon']}")
        st.markdown(f"### {colores_defcon.get(data['defcon'], 'DESCONOCIDO')}")
        st.metric(label="Puntaje de Tensión (Score)", value=f"{data['score']} pts")
        st.caption(f"Última actualización (UTC): {data['timestamp']}")
        
    with col2:
        st.subheader("Radar de Eventos Confirmados")
        if data["score"] == 0:
            st.success("✅ Tráfico aéreo y fuentes oficiales dentro de los parámetros de paz. No hay anomalías.")
        else:
            for evento in data["triggers"]:
                if "CRÍTICO" in evento:
                    st.error(evento)  # Rojo para eventos críticos
                else:
                    st.warning(evento) # Amarillo para advertencias

# --- PESTAÑA 2: PREDICCIÓN TIMESFM-3 ---
with tab_predict:
    st.subheader("Tendencia Histórica y Proyección TimesFM-3")
    st.markdown("Este módulo utiliza IA para modelar series temporales y anticipar escaladas geopolíticas basadas en el historial del puntaje de tensión.")
    
    if historial_disponible:
        # Mostrar el pasado (Curva real en rojo)
        st.line_chart(df_historial.set_index("timestamp")["score"], color="#ff4b4b")
        
        # MÓDULO PREDICTIVO (El Seguro de Arranque)
        registros_actuales = len(df_historial)
        registros_necesarios = 96 # Aprox 24 horas de datos
        
        st.divider()
        if registros_actuales >= registros_necesarios:
            st.success("🧠 Dataset maduro. TimesFM-3 está listo para procesar la proyección de alertas futuras.")
            # Aquí inyectaremos el código de predicción de TimesFM
        else:
            st.info("Calibrando modelo predictivo...")
            progreso = int((registros_actuales / registros_necesarios) * 100)
            st.progress(max(0, min(progreso, 100)) / 100.0)
            st.caption(f"Recopilando volumen de datos históricos necesarios para la predicción algorítmica: {registros_actuales}/{registros_necesarios} ciclos (1 ciclo = 15 min).")
    else:
        st.info("Aún no hay datos históricos suficientes. El motor generará el primer punto en el próximo barrido del radar.")

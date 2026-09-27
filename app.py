import streamlit as st
import json

st.set_page_config(page_title="Radar OSINT Global", page_icon="🌍", layout="wide")

st.title("🌍 Sistema de Alertas Global OSINT")
st.markdown("Monitor de tensiones y movimientos estratégicos en tiempo real.")
st.divider()

# Intentar leer los datos guardados por GitHub Actions
try:
    with open("datos.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {
        "defcon": 5, 
        "score": 0, 
        "triggers": ["Esperando la primera ejecución del radar..."], 
        "timestamp": "Desconocido"
    }

col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.subheader("Estado de Alerta")
    colores_defcon = {
        1: "🔴 CRÍTICO", 2: "🟠 ESCALADA", 3: "🟡 PREVENCIÓN", 
        4: "🔵 MONITOREO", 5: "🟢 RUTINA"
    }
    estado_texto = colores_defcon.get(data["defcon"], "DESCONOCIDO")
    
    st.metric(label="Nivel DEFCON", value=f"Nivel {data['defcon']}")
    st.markdown(f"### {estado_texto}")
    st.metric(label="Puntaje de Tensión (Score)", value=f"{data['score']} pts")
    st.caption(f"Última actualización (UTC): {data['timestamp']}")

with col_der:
    st.subheader("Radar de Eventos (Triggers)")
    if data["score"] == 0:
        st.success("✅ Tráfico aéreo y fuentes oficiales dentro de los parámetros de paz. No hay anomalías.")
    else:
        for evento in data["triggers"]:
            st.warning(evento)

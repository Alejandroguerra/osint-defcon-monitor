import os
import smtplib
from email.mime.text import MIMEText
import requests
import feedparser
from datetime import datetime
import json  # <--- AGREGA ESTA LÍNEA AQUÍ
import csv
import os

# ==========================================
# CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ==========================================
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

# ==========================================
# MOTOR DE PUNTUACIÓN Y UMBRALES DEFCON
# ==========================================
# La suma de puntos determinará el nivel de alerta
SCORE_WEIGHTS = {
    "RSS_CRITICAL": 10,      # Declaración aislada (bajo peso por sí sola)
    "RSS_WARNING": 2,        # Advertencia diplomática aislada
    "MIL_DOOMSDAY": 15,      # Avión de mando aislado
    "MIL_STRATEGIC_BOMBER": 25, # Bombardero estratégico aislado
    "VIP_JET_UNUSUAL": 15,   # Éxodo VIP aislado
    "MIL_LOGISTICS": 2,      # Logística común aislada
    "CORRELATION_BONUS": 60  # 🔴 ¡EL GOLPE MAESTRO! Bono masivo si hay Declaración + Movimiento simultáneo
}

def get_defcon_level(score):
    """Convierte el puntaje matemático a un nivel DEFCON (5 a 1)."""
    if score >= 100: return 1
    if score >= 50:  return 2
    if score >= 25:  return 3
    if score >= 10:  return 4
    return 5

# ==========================================
# DICCIONARIOS DE INTELIGENCIA
# ==========================================
# Códigos Hex ICAO24 de aviones críticos
DOOMSDAY_PLANES = {"adfed5", "adfeba", "adfebc"} # Ejemplos genéricos E-4B
VIP_JETS = {"400123", "a1b2c3"} # Ejemplos de Jets de oligarcas

KEYWORDS_WARNING = ["mobilization", "evacuation", "consequences", "alert status"]
KEYWORDS_CRITICAL = ["nuclear", "strike", "state of war", "defcon", "immediate retaliation"]

OFFICIAL_FEEDS = {
    "DoD USA": "https://www.defense.gov/DesktopModules/ArticleCS/RSS.aspx?ContentType=400&Site=945",
    "MoD UK": "https://www.gov.uk/government/organisations/ministry-of-defence.atom",
    "MoD France": "https://www.defense.gouv.fr/rss.xml",
    "Russia TASS (State)": "https://tass.com/rss/v2.xml",
    "China Xinhua (State)": "http://www.xinhuanet.com/english/rss/worldrss.xml"
}
# ==========================================
# FUNCIONES DE RECOLECCIÓN
# ==========================================
def scan_air_traffic():
    """Analiza el tráfico aéreo y retorna puntos y hallazgos."""
    points = 0
    triggers = []
    
    try:
        response = requests.get("https://opensky-network.org/api/states/all", timeout=10)
        if response.status_code != 200:
            return points, triggers
            
        states = response.json().get("states", []) or []
        logistics_count = 0
        
        for s in states:
            icao24 = s[0].lower()
            callsign = s[1].strip() if s[1] else ""
            
            # 1. Detectar aviones Doomsday / Mando Estratégico
            if icao24 in DOOMSDAY_PLANES:
                points += SCORE_WEIGHTS["MIL_DOOMSDAY"]
                triggers.append(f"[DOOMSDAY] Avión de mando detectado: {icao24} ({callsign})")
                
            # 2. Detectar éxodo de Jets VIP
            if icao24 in VIP_JETS:
                points += SCORE_WEIGHTS["VIP_JET_UNUSUAL"]
                triggers.append(f"[VIP JET] Movimiento detectado: {icao24}")
                
            # 3. Detectar logística militar en masa
                
            if callsign.startswith(("RCH", "RRR", "CMB", "CTM", "RFF")):
                logistics_count += 1
                
        # Calcular enjambres logísticos (cada 3 aviones suman peso)
        if logistics_count >= 3:
            pts_logistica = (logistics_count // 3) * SCORE_WEIGHTS["MIL_LOGISTICS"]
            points += pts_logistica
            triggers.append(f"[LOGÍSTICA] Enjambre detectado: {logistics_count} aviones de transporte militar")

    except Exception as e:
        triggers.append(f"[ERROR] Fallo en API aérea: {str(e)}")
        
    return points, triggers

def scan_rss_feeds():
    """Analiza noticias oficiales y retorna puntos y hallazgos."""
    points = 0
    triggers = []
    
    for source, url in OFFICIAL_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]: # Revisar las últimas 3 noticias
                text = f"{entry.title} {entry.get('summary', '')}".lower()
                
                # Buscar palabras críticas (Nivel 1/2)
                if any(k in text for k in KEYWORDS_CRITICAL):
                    points += SCORE_WEIGHTS["RSS_CRITICAL"]
                    triggers.append(f"[CRÍTICO - {source}] {entry.title}")
                    
                # Buscar palabras de advertencia (Nivel 3/4)
                elif any(k in text for k in KEYWORDS_WARNING):
                    points += SCORE_WEIGHTS["RSS_WARNING"]
                    triggers.append(f"[ADVERTENCIA - {source}] {entry.title}")
                    
        except Exception:
            continue
            
    return points, triggers

# ==========================================
# ENVÍO DE ALERTAS
# ==========================================
def dispatch_alert(defcon, score, triggers):
    """Envía correo si se superó el umbral (DEFCON 3, 2 o 1)."""
    if defcon > 3:
        print(f"DEFCON {defcon} (Puntos: {score}). Todo dentro de los parámetros. No se requiere alerta.")
        return

    subject = f"🚨 [ALERTA OSINT DEFCON {defcon}] Puntaje Crítico: {score}"
    
    body = f"SISTEMA DE ALERTA TEMPRANA - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    body += "-" * 50 + "\n"
    body += f"NIVEL CALCULADO: DEFCON {defcon}\n"
    body += f"PUNTAJE TOTAL:   {score} puntos\n"
    body += "-" * 50 + "\n\n"
    body += "VECTORES DETECTADOS:\n"
    for t in triggers:
        body += f" • {t}\n"

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Alerta DEFCON {defcon} enviada exitosamente al correo.")
    except Exception as e:
        print(f"Error crítico enviando correo: {e}")

# ==========================================
# GUARDADO PARA EL TABLERO WEB
# ==========================================
def guardar_datos_tablero(defcon, score, triggers):
    """Guarda los resultados en un archivo JSON para que Streamlit los lea."""
    datos = {
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "defcon": defcon,
        "score": score,
        "triggers": triggers
    }
    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

# ==========================================
# GUARDADO DE MEMORIA HISTÓRICA (NUEVO)
# ==========================================
def guardar_historial_csv(defcon, score):
    """Guarda un registro continuo para la futura IA predictiva."""
    archivo_csv = "historial.csv"
    archivo_existe = os.path.isfile(archivo_csv)
    
    with open(archivo_csv, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not archivo_existe:
            writer.writerow(["timestamp", "defcon", "score"])
        
        timestamp_actual = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([timestamp_actual, defcon, score])


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("Iniciando barrido OSINT...")
    
    total_score = 0
    all_triggers = []
    
    # 1. Recolectar datos y puntajes
    pts_air, trg_air = scan_air_traffic()
    pts_rss, trg_rss = scan_rss_feeds()
    
# ==========================================
    # 2. Consolidar la matriz y aplicar correlación táctica
    # ==========================================
    total_score = pts_air + pts_rss
    all_triggers.extend(trg_air)
    all_triggers.extend(trg_rss)

    # Detectar si hay cruce simultáneo (Declaración crítica + Movimiento militar activo)
    hubo_declaracion_critica = any("CRÍTICO" in t for t in trg_rss)
    hubo_movimiento_militar = pts_air > 0

    if hubo_declaracion_critica and hubo_movimiento_militar:
        total_score += SCORE_WEIGHTS["CORRELATION_BONUS"]
        all_triggers.insert(0, "🚨 [CORRELACIÓN ESTRATÉGICA CRÍTICA] Convergencia detectada: Declaración oficial agresiva respaldada por actividad militar en curso.")

    # ==========================================
    # 3. Calcular estado y alertar
    # ==========================================
    current_defcon = get_defcon_level(total_score)
    dispatch_alert(current_defcon, total_score, all_triggers)
# 4. Guardar datos para el tablero de Streamlit  <--- AGREGA ESTO
    guardar_datos_tablero(current_defcon, total_score, all_triggers)

# 5. Guardar memoria histórica
    guardar_historial_csv(current_defcon, total_score)

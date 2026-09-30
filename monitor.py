import os
import smtplib
from email.mime.text import MIMEText
import requests
import feedparser
from datetime import datetime
import json  
import csv


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
    "RSS_CRITICAL": 10,       # Declaración aislada
    "RSS_WARNING": 2,         # Advertencia aislada
    "MIL_DOOMSDAY": 30,       # Comando estratégico
    "MIL_STRATEGIC_BOMBER": 40, # Bombarderos o activos de largo alcance
    "MIL_AWACS_TANKER": 30,   # Aviones de alerta temprana o cisternas
    "VIP_JET_UNUSUAL": 45,    # 🔴 ¡PESO MÁXIMO! Éxodo o movimiento VIP (Indicador primario de crisis)
    "MIL_LOGISTICS_HEAVY": 5, # Transporte masivo
    "CORRELATION_BONUS": 50   # Bono por convergencia
}
# Listas globales de activos especiales (necesarias para evitar el NameError)
STRATEGIC_ASSETS = [
    "AE11EB", # Códigos ICAO de ejemplo para bombarderos o activos clave
]

DOOMSDAY_PLANES = [
    # Agrega aquí los códigos ICAO de aviones de mando estratégico si los tienes
]

VIP_JETS = [
    # Agrega aquí los códigos ICAO de jets privados o flotas de élite
]
def get_defcon_level(score):
    """Calcula el nivel de DEFCON con umbrales altamente cautos para evitar cualquier aviso prematuro."""
    if score >= 120:
        return 1  # 🔴 DEFCON 1: Emergencia extrema e inobjetable (Exige convergencia masiva)
    elif score >= 95:
        return 2  # 🟠 DEFCON 2: Escalada grave confirmada 
    elif score >= 70:
        return 3  # 🟡 DEFCON 3: Prevención seria (Primer y único nivel que envía correo de alerta)
    elif score >= 35:
        return 4  # 🔵 DEFCON 4: Monitoreo superior de rutina
    else:
        return 5  # 🟢 DEFCON 5: Paz / Operación completamente normal
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
    """Analiza el tráfico aéreo clasificando aeronaves y priorizando flotas clave."""
    points = 0
    triggers = []
    logistics_count = 0
    aviones_detectados = []
    
    try:
        url = "https://opensky-network.org/api/states/all"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return 0, []
            
        states = response.json().get("states", [])
        if not states:
            return 0, []
            
        for s in states:
            icao24 = s[0]
            callsign = s[1].strip() if s[1] else ""
            on_ground = s[8]
            
            if on_ground:
                continue
                
            # Guardamos el avión detectado en la lista para evaluarlo
            aviones_detectados.append({"icao24": icao24, "callsign": callsign})
            
            # 1. Activos Estratégicos Superiores (Bombarderos / Mando)
            if icao24 in STRATEGIC_ASSETS or icao24 in DOOMSDAY_PLANES:
                points += SCORE_WEIGHTS["MIL_STRATEGIC_BOMBER"]
                triggers.append(f"[CRÍTICO - AIRE] Activo estratégico de alto valor detectado: {icao24} ({callsign})")
                
            # 2. Aviones de Alerta Temprana (AWACS) o Cisternas
            elif callsign.startswith(("REACH", "RSV", "COBRA", "DRAGON")):
                points += SCORE_WEIGHTS["MIL_AWACS_TANKER"]
                triggers.append(f"[ALERTA - SOPORTE TÁCTICO] Activo de reabastecimiento o control aéreo detectado: {callsign}")
                
            # 3. Éxodo VIP
            elif icao24 in VIP_JETS:
                points += SCORE_WEIGHTS["VIP_JET_UNUSUAL"]
                triggers.append(f"[VIP - ÉXODO] Movimiento de avión privado de alto nivel: {icao24} ({callsign})")
                
            # 4. Logística Militar Común
            elif callsign.startswith(("RCH", "RRR", "CMB", "CTM", "RFF")):
                logistics_count += 1
                
        if logistics_count >= 12:
            points += SCORE_WEIGHTS["MIL_LOGISTICS_HEAVY"]
            triggers.append(f"[LOGÍSTICA PESADA] Concentración masiva anómala de transporte militar: {logistics_count} unidades simultáneas")
            
        # Ejecutamos la evaluación detallada de flotas prioritarias
        pts_flotas, trg_flotas = evaluar_flotas_prioritarias(aviones_detectados)
        points += pts_flotas
        triggers.extend(trg_flotas)
        
    except Exception as e:
        triggers.append(f"[ERROR] Fallo en API aérea: {str(e)}")
        
    return points, triggers

def evaluar_flotas_prioritarias(aviones_detectados):
    """Evalúa flotas prioritarias (VIPs y activos estratégicos) frente al umbral de normalidad."""
    puntos_aereos = 0
    triggers_aereos = []
    
    # Filtrar aeronaves de alto valor detectadas en el espacio aéreo activo
    vip_encontrados = [av for av in aviones_detectados if av.get("icao24") in VIP_JETS]
    estrategicos_encontrados = [av for av in aviones_detectados if av.get("icao24") in STRATEGIC_ASSETS]
    
    # Asignar peso prioritario si se detectan anomalías en flotas ejecutivas o gubernamentales
    if len(vip_encontrados) > 0:
        puntos_aereos += SCORE_WEIGHTS["VIP_JET_UNUSUAL"] * len(vip_encontrados)
        triggers_aereos.append(f"🚨 [FLOTA VIP] Movimiento crítico detectado de aeronaves de élite: {len(vip_encontrados)} unidad(es).")
        
    if len(estrategicos_encontrados) > 0:
        puntos_aereos += SCORE_WEIGHTS["MIL_STRATEGIC_BOMBER"] * len(estrategicos_encontrados)
        triggers_aereos.append(f"🚨 [ACTIVO ESTRATÉGICO] Despliegue de bombardero/mando detectado: {len(estrategicos_encontrados)} unidad(es).")
        
    return puntos_aereos, triggers_aereos


# ==========================================
# NUEVO: FILTRO DE CONTEXTO RELACIONAL (DOBLE VERIFICACIÓN)
# ==========================================
def analizar_contexto_titular(titulo):
    """Analiza el titular buscando relaciones estrictas: Actor Clave + Ataque, descartando diplomacia."""
    titulo_lower = titulo.lower()
    
    # 1. Filtro estricto de exclusión por tono diplomático o amistoso
    frases_amistosas = ["friend", "peace", "talks", "summit", "dialogue", "ceasefire", "agreement", "calls ... friend"]
    if any(frase in titulo_lower for frase in frases_amistosas) or "friend" in titulo_lower:
        return 0, None  
        
    # 2. Actores clave obligatorios
    actores = ["russia", "iran", "ukraine", "israel", "china", "us", "kremlin", "tehran"]
    tiene_actor = any(actor in titulo_lower for actor in actores)
    
    # 3. Acciones ofensivas de envergadura obligatorias
    acciones_ofensivas = ["strike", "massive attack", "bombardment", "missile barrage", "offensive", "launch", "invasion"]
    tiene_ataque = any(accion in titulo_lower for accion in acciones_ofensivas)
    
    # 4. Validación cruzada de contenido crítico
    if tiene_actor and tiene_ataque:
        return SCORE_WEIGHTS["RSS_CRITICAL"], f"[CRÍTICO - RSS] Convergencia Actor-Ataque detectada: {titulo}"
        
    # 5. Advertencias secundarias
    palabras_warning = ["tension", "warning", "mobilization", "border buildup"]
    if any(w in titulo_lower for w in palabras_warning):
        return SCORE_WEIGHTS["RSS_WARNING"], f"[ADVERTENCIA - RSS] Tensión menor: {titulo}"
        
    return 0, None


def scan_rss_feeds():
    """Analiza noticias oficiales aplicando el filtro relacional de contexto."""
    points = 0
    triggers = []
    
    for source, url in OFFICIAL_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]: # Revisar las últimas 3 noticias
                # Aplicamos la nueva función de análisis contextual estricto
                pts_noticia, trigger_noticia = analizar_contexto_titular(entry.title)
                if pts_noticia > 0 and trigger_noticia:
                    points += pts_noticia
                    triggers.append(f"[{source}] {trigger_noticia}")
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
def guardar_datos_tablero(defcon, score, triggers, aviones_mapa=None):
    """Guarda los resultados en un archivo JSON para que Streamlit los lea."""
    if aviones_mapa is None:
        aviones_mapa = []
        
    datos = {
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "defcon": defcon,
        "score": score,
        "triggers": triggers,
        "aviones_mapa": aviones_mapa
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
# EJECUCIÓN PRINCIPAL CON DOBLE VERIFICACIÓN
# ==========================================
if __name__ == "__main__":
    print("Iniciando barrido OSINT con doble verificación...")
    
    total_score = 0
    all_triggers = []
    
    # 1. Recolectar datos y puntajes independientes
    pts_air, trg_air = scan_air_traffic()
    pts_rss, trg_rss = scan_rss_feeds()
    
    all_triggers.extend(trg_air)
    all_triggers.extend(trg_rss)

    # ==========================================
    # 2. Consolidación de matriz con regla de doble factor
    # ==========================================
    pts_rss_ajustado = pts_rss * 0.5  # La retórica sola pierde peso masivo
    hubo_movimiento_fisico = pts_air > 0
    hubo_declaracion_critica = any("CRÍTICO" in t for t in trg_rss)

    if hubo_declaracion_critica and hubo_movimiento_fisico:
        total_score = pts_rss + pts_air + SCORE_WEIGHTS["CORRELATION_BONUS"]
        all_triggers.insert(0, "🚨 [DOBLE VERIFICACIÓN CONFIRMADA] Declaración oficial respaldada por actividad física simultánea en el radar.")
    elif hubo_declaracion_critica and not hubo_movimiento_fisico:
        total_score = min(pts_rss_ajustado + pts_air, 15) 
        all_triggers.append("ℹ️ [RETORICA SIN RESPALDO FÍSICO] Declaración detectada sin correlación de movimiento militar en el ciclo.")
    else:
        total_score = pts_rss + pts_air

    # ==========================================
    # 3. Calcular estado y alertar
    # ==========================================
    current_defcon = get_defcon_level(total_score)
    dispatch_alert(current_defcon, total_score, all_triggers)
    
    # 4. Guardar datos para el tablero de Streamlit
    guardar_datos_tablero(current_defcon, total_score, all_triggers, aviones_mapa=[])

    # 5. Guardar memoria histórica en CSV
    guardar_historial_csv(current_defcon, total_score)

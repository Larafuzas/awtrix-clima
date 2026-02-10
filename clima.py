import os
import requests
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone, timedelta

# 1. OBTENER VARIABLES SECRETAS
LAT = os.environ["LATITUD"]
LON = os.environ["LONGITUD"]
API_KEY = os.environ["OWM_API_KEY"]
BROKER = os.environ["MQTT_BROKER"]
PREFIX = os.environ["MQTT_PREFIX"]

TOPIC = f"{PREFIX}custom/tiempo"

# 2. DEFINICIÓN DE ICONOS (IDs de Awtrix)
ICON_TORMENTA = "2288"
ICON_VIENTO   = "55032"
ICON_NIEVE    = "2289"
ICON_LLUVIA   = "53674"
ICON_NIEBLA   = "59539"
ICON_NUBES    = "2283"

# Iconos dinámicos (Día / Noche)
ICON_SOL      = "2282"
ICON_LUNA     = "12181"   # Nueva luna despejada
ICON_POCAS_NUBES_DIA = "67868"
ICON_POCAS_NUBES_NOCHE = "12195"

def get_weather():
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=es"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # --- DATOS BÁSICOS ---
        temp = round(data["main"]["temp"])
        weather_id = data["weather"][0]["id"] # El código numérico (ej: 500, 800)
        
        # --- CÁLCULO DÍA/NOCHE (ASTRONÓMICO) ---
        sunrise = data["sys"]["sunrise"]
        sunset = data["sys"]["sunset"]
        now = data["dt"]
        
        # True si es de día, False si es de noche
        is_day = sunrise <= now < sunset

        # --- SISTEMA DE PRIORIDADES POR ALERTAS (Condicionales) ---
        
        # 1. TORMENTA (Grupo 2xx: 200-232)
        if 200 <= weather_id <= 232:
            awtrix_icon = ICON_TORMENTA

        # 2. ALERTA DE VIENTO EXTREMO (771: Squalls, 781: Tornado)
        # (También incluimos la serie 9xx por seguridad)
        elif weather_id == 771 or weather_id == 781 or (900 <= weather_id <= 962):
            awtrix_icon = ICON_VIENTO

        # 3. NIEVE (Grupo 6xx: 600-622)
        elif 600 <= weather_id <= 622:
            awtrix_icon = ICON_NIEVE

        # 4. LLUVIA (Grupo 3xx: Drizzle, Grupo 5xx: Rain)
        elif (300 <= weather_id <= 321) or (500 <= weather_id <= 531):
            awtrix_icon = ICON_LLUVIA

        # 5. NIEBLA / ATMÓSFERA (Grupo 7xx: 701-762)
        elif 701 <= weather_id <= 762:
            awtrix_icon = ICON_NIEBLA

        # 6. CIELO DESPEJADO (800)
        elif weather_id == 800:
            if is_day:
                awtrix_icon = ICON_SOL
            else:
                awtrix_icon = ICON_LUNA

        # 7. POCAS NUBES (801: 11-25%)
        elif weather_id == 801:
            if is_day:
                awtrix_icon = ICON_POCAS_NUBES_DIA
            else:
                awtrix_icon = ICON_POCAS_NUBES_NOCHE

        # 8. RESTO DE NUBES (802, 803, 804) - Usamos el mismo para día y noche
        else:
            awtrix_icon = ICON_NUBES
            
        return temp, awtrix_icon
        
    except Exception as e:
        print(f"Error: {e}")
        raise e

def send_to_awtrix(temp, icon):
    payload = {
        "text": f"{temp}°C",
        "icon": icon,
        "pushIcon": 2,
        "color": "#FFFFFF"
    }
    
    client = mqtt.Client()
    client.connect(BROKER, 1883, 60)
    client.publish(TOPIC, json.dumps(payload), retain=True)
    client.disconnect()
    print(f"Enviado: {temp}°C con icono {icon} (ID Clima)")

if __name__ == "__main__":
    t, i = get_weather()
    send_to_awtrix(t, i)

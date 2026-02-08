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

# 2. MAPEO DE ICONOS
icon_map = {
    # SOL / LUNA
    "01d": "2282", "01n": "962",
    # POCAS NUBES
    "02d": "67868","02n": "12195",
    # NUBES
    "03d": "2283", "03n": "2283",
    "04d": "2283", "04n": "2283",
    # LLUVIA
    "09d": "53674","09n": "53674",
    "10d": "53674","10n": "53674",
    # TORMENTA
    "11d": "2288", "11n": "2288",
    # NIEVE
    "13d": "2289", "13n": "2289",
    # NIEBLA
    "50d": "59539","50n": "59539",
    # NUEVO: VIENTO
    "wind": "55032"
}

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=es"
    response = requests.get(url)
    data = response.json()
    
    # Datos básicos
    temp = round(data["main"]["temp"])
    code = data["weather"][0]["icon"]
    wind_speed = data["wind"]["speed"] # Metros por segundo
    
    # --- LÓGICA DE TIEMPO ---
    # Calculamos la hora local real usando el 'timezone' de la API
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(seconds=data.get("timezone", 0))
    
    # REGLA 1: Forzar Día a partir de las 07:00 AM
    # Si son las 7 o más, cambiamos cualquier 'n' (noche) por 'd' (día)
    if local_time.hour >= 7:
        code = code.replace('n', 'd')

    # --- LÓGICA DE VIENTO ---
    # REGLA 2: Si el viento supera 5.5 m/s (~20 km/h), priorizamos icono de viento
    if wind_speed > 5.5:
        icon_key = "wind"
    else:
        icon_key = code
    
    # Seleccionar ID final (si falla, usa nube 2283)
    icon_id = icon_map.get(icon_key, "2283")
    
    return temp, icon_id

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
    print(f"Enviado: {temp}°C con icono {icon}")

if __name__ == "__main__":
    try:
        t, i = get_weather()
        send_to_awtrix(t, i)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

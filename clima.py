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
    # NIEBLA (Mist/Fog)
    "50d": "59539","50n": "59539",
    # ESPECIAL: VIENTO
    "wind": "55032"
}

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=es"
    response = requests.get(url)
    data = response.json()
    
    # Datos básicos
    temp = round(data["main"]["temp"])
    icon_code = data["weather"][0]["icon"]
    weather_id = data["weather"][0]["id"]
    
    # --- LÓGICA DE TIEMPO (Hora local exacta) ---
    # Usamos el 'timezone' que nos da la API para saber tu hora real
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(seconds=data.get("timezone", 0))
    
    # --- LÓGICA 1: DETECCIÓN DE VIENTO POR CÓDIGO ---
    # Buscamos códigos específicos de viento en la documentación de OWM:
    # 771: Squalls (Ráfagas)
    # 781: Tornado
    # 9xx: Códigos adicionales (905=Windy, 951-962=Beaufort Scale)
    is_windy = False
    if weather_id == 771 or weather_id == 781:
        is_windy = True
    elif 900 <= weather_id <= 962: # Rango completo de códigos 'Extreme' y 'Additional'
        is_windy = True

    # --- LÓGICA 2: SELECCIÓN DE ICONO ---
    if is_windy:
        # Prioridad absoluta: Si hay código de viento, ponemos el icono de viento
        key_final = "wind"
    else:
        # Si no es viento, usamos el código visual normal (01d, 02n, etc.)
        key_final = icon_code

        # --- LÓGICA 3: FORZAR DÍA A PARTIR DE LAS 07:00 ---
        # Solo aplicamos esto si NO es viento (el viento no tiene día/noche)
        # Si la hora local es 7 o mayor, cambiamos 'n' (noche) por 'd' (día)
        if local_time.hour >= 7:
            key_final = key_final.replace('n', 'd')

    # Recuperar el ID de Awtrix del mapa
    awtrix_icon = icon_map.get(key_final, "2283")
    
    return temp, awtrix_icon

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

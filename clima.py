import os
import requests
import json
import time
import paho.mqtt.client as mqtt

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
    # VIENTO (Si hay alerta)
    "wind": "55032"
}

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=es"
    response = requests.get(url)
    data = response.json()
    
    # --- DATOS BÁSICOS ---
    temp = round(data["main"]["temp"])
    weather_id = data["weather"][0]["id"]      # ID numérico (ej: 800, 500)
    original_icon = data["weather"][0]["icon"] # Icono original (ej: "04n")
    
    # --- DATOS ASTRONÓMICOS ---
    # OpenWeather nos da el timestamp unix del amanecer y anochecer de HOY
    sunrise = data["sys"]["sunrise"]
    sunset = data["sys"]["sunset"]
    now = data["dt"] # Hora actual del reporte
    
    # --- LÓGICA 1: ¿ES DE DÍA O DE NOCHE? (Matemática pura) ---
    if sunrise <= now < sunset:
        suffix = 'd' # Es de día
    else:
        suffix = 'n' # Es de noche
        
    # --- LÓGICA 2: CONSTRUCCIÓN DEL CÓDIGO ---
    # Cogemos el código base (los dos primeros números, ej: "02") y le pegamos nuestro sufijo calculado
    base_code = original_icon[:2] # "01", "02", "10"...
    calculated_icon_key = f"{base_code}{suffix}"
    
    # --- LÓGICA 3: EXCEPCIÓN DE VIENTO ---
    # Si hay códigos de viento fuerte (771, 781, 9xx), esto tiene prioridad sobre el sol/luna
    is_windy = False
    if weather_id == 771 or weather_id == 781:
        is_windy = True
    elif 900 <= weather_id <= 962:
        is_windy = True
        
    if is_windy:
        final_key = "wind"
    else:
        final_key = calculated_icon_key

    # Buscamos el ID de Awtrix
    # Si por lo que sea la clave no existe, usamos la nube (2283) por defecto
    awtrix_icon = icon_map.get(final_key, "2283")
    
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

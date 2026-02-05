import os
import requests
import json
import paho.mqtt.client as mqtt

# 1. OBTENER VARIABLES SECRETAS
LAT = os.environ["LATITUD"]
LON = os.environ["LONGITUD"]
API_KEY = os.environ["OWM_API_KEY"]
BROKER = os.environ["MQTT_BROKER"]
PREFIX = os.environ["MQTT_PREFIX"] # <--- Nueva variable secreta

# Construimos el topic usando el prefijo secreto
TOPIC = f"{PREFIX}custom/tiempo"

# 2. MAPEO DE ICONOS (El resto sigue igual...)
icon_map = {
    "01d": "2282", "01n": "962",
    "02d": "67868","02n": "12195",
    "03d": "2283", "03n": "2283",
    "04d": "2283", "04n": "2283",
    "09d": "53674","09n": "53674",
    "10d": "53674","10n": "53674",
    "11d": "2288", "11n": "2288",
    "13d": "2289", "13n": "2289",
    "50d": "59539","50n": "59539"
}

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=es"
    response = requests.get(url)
    data = response.json()
    
    temp = round(data["main"]["temp"])
    code = data["weather"][0]["icon"]
    
    # Elegir icono o usar nube por defecto
    icon = icon_map.get(code, "2283")
    
    return temp, icon

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

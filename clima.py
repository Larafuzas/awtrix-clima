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
    "01d": "2282", 
    "01n": "12181", # <--- CAMBIO: Nueva Luna Despejada
    
    # POCAS NUBES
    "02d": "67868","02n": "12195",
    
    # NUBES DISPERSAS / NUBLADO
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
    
    # VIENTO (Solo si hay alerta)
    "wind": "55032"
}

def get_weather():
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=es"
        response = requests.get(url)
        response.raise_for_status() # Lanza error si la API falla
        data = response.json()
        
        # --- DATOS BÁSICOS ---
        temp = round(data["main"]["temp"])
        weather_id = data["weather"][0]["id"]
        original_icon = data["weather"][0]["icon"] # Ej: "01n"
        
        # --- DATOS ASTRONÓMICOS (Orto y Ocaso de HOY) ---
        sunrise = data["sys"]["sunrise"]
        sunset = data["sys"]["sunset"]
        now = data["dt"] # Hora actual del reporte
        
        # --- LÓGICA 1: DETERMINAR DÍA O NOCHE (Matemática) ---
        # Si la hora actual está entre el amanecer y el anochecer -> Día
        if sunrise <= now < sunset:
            suffix = 'd' 
        else:
            suffix = 'n' 
            
        # --- LÓGICA 2: CONSTRUIR LA CLAVE DEL ICONO ---
        # Cogemos el código numérico base (ej: "01" de "01n") y le pegamos el sufijo calculado
        base_code = original_icon[:2] # "01", "02"...
        calculated_key = f"{base_code}{suffix}"
        
        # --- LÓGICA 3: EXCEPCIÓN DE VIENTO ---
        # Si hay códigos de viento fuerte, tienen prioridad
        is_windy = False
        if weather_id == 771 or weather_id == 781: # Squalls, Tornado
            is_windy = True
        elif 900 <= weather_id <= 962: # Códigos extremos/adicionales
            is_windy = True
            
        if is_windy:
            final_key = "wind"
        else:
            final_key = calculated_key

        # Buscar el ID de Awtrix en nuestro mapa
        awtrix_icon = icon_map.get(final_key, "2283") # 2283 es el fallback (nube)
        
        return temp, awtrix_icon
        
    except Exception as e:
        print(f"Error obteniendo clima: {e}")
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
    print(f"Enviado: {temp}°C con icono {icon}")

if __name__ == "__main__":
    t, i = get_weather()
    send_to_awtrix(t, i)

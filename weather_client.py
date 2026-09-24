import sys
import json
import config
import gc

try:
    import urequests as requests
    IS_MICROPYTHON = True
except ImportError:
    import requests
    IS_MICROPYTHON = False

def http_get_json(url):
    """Realiza solicitud HTTP GET y retorna objeto JSON."""
    if IS_MICROPYTHON:
        gc.collect()
        response = None
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            print(f"[HTTP] Error en solicitud HTTP: {e}")
            raise e
        finally:
            if response:
                response.close()
            gc.collect()
    else:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[HTTP] Error en solicitud HTTP: {e}")
            raise e

def get_location_coordinates():
    """Detecta la ubicación automáticamente vía IP pública o usa configuración."""
    actual_region = config.REGIONS.get("actual", {})
    lat = actual_region.get("latitude")
    lon = actual_region.get("longitude")
    if lat is not None and lon is not None:
        return lat, lon, "Ubicación Configurada"
        
    print("[Location] Detectando ubicación vía IP pública...")
    url = "http://ip-api.com/json/"
    try:
        data = http_get_json(url)
        if data.get("status") == "success":
            lat, lon = data.get("lat"), data.get("lon")
            city, country = data.get("city"), data.get("country")
            print(f"[Location] Ubicación: {city}, {country} ({lat}, {lon})")
            return lat, lon, f"{city}, {country}"
        else:
            raise ValueError("API geolocalización falló.")
    except Exception as e:
        print(f"[Location] Usando ubicación de respaldo: {e}")
        return -34.6037, -58.3816, "Buenos Aires, Argentina (Respaldo)"

def get_current_weather(latitude, longitude):
    """Consulta Open-Meteo para el clima actual en las coordenadas."""
    url = f"http://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code,is_day&timezone=auto"
    try:
        data = http_get_json(url)
        current = data.get("current", {})
        
        temp = current.get("temperature_2m")
        code = current.get("weather_code")
        is_day = current.get("is_day")
        
        print(f"[Weather] Clima obtenido -> Temp: {temp}°C | Code: {code} | IsDay: {is_day}")
        
        return {
            "temperature": temp,
            "weather_code": code,
            "is_day": is_day,
            "daily": {},
            "raw": {"current_weather": {"temperature": temp, "weathercode": code, "is_day": is_day}}
        }
    except Exception as e:
        print(f"[Weather] Error al consultar datos del clima: {e}")
        return None
    finally:
        gc.collect()

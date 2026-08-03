import sys
import json
import config

try:
    import urequests as requests
    IS_MICROPYTHON = True
except ImportError:
    import requests
    IS_MICROPYTHON = False

def http_get_json(url):
    """
    Performs an HTTP GET request and returns the parsed JSON object.
    Ensures that sockets are closed on MicroPython to prevent memory leaks.
    """
    if IS_MICROPYTHON:
        response = None
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            print(f"[HTTP] Error en solicitud HTTP a {url}: {e}")
            raise e
        finally:
            if response:
                response.close()
    else:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[HTTP] Error en solicitud HTTP a {url}: {e}")
            raise e

def get_location_coordinates():
    """
    Queries ip-api.com to automatically detect public IP-based coordinates.
    Returns a tuple of (latitude, longitude).
    """
    actual_region = config.REGIONS.get("actual", {})
    lat = actual_region.get("latitude")
    lon = actual_region.get("longitude")
    if lat is not None and lon is not None:
        return lat, lon, "Ubicación Configurada"
        
    print("[Location] Detectando ubicación automáticamente vía IP pública...")
    url = "http://ip-api.com/json/"
    try:
        data = http_get_json(url)
        if data.get("status") == "success":
            lat = data.get("lat")
            lon = data.get("lon")
            city = data.get("city")
            country = data.get("country")
            print(f"[Location] Ubicación detectada: {city}, {country} (Lat: {lat}, Lon: {lon})")
            return lat, lon, f"{city}, {country}"
        else:
            raise ValueError("La API de geolocalización devolvió un estado fallido.")
    except Exception as e:
        print(f"[Location] Error al geolocalizar de forma automática: {e}")
        # Fallback to Buenos Aires, Argentina
        fallback_lat, fallback_lon = -34.6037, -58.3816
        return fallback_lat, fallback_lon, "Buenos Aires, Argentina (Respaldo)"

def get_current_weather(latitude, longitude):
    """
    Queries Open-Meteo for the current weather at the specified coordinates.
    Prints the raw API response JSON to the console.
    Returns a dictionary with temperature, weather code, is_day status, and the raw payload.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code,is_day&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto"
    
    try:
        data = http_get_json(url)
        
        # 1. Print raw JSON response to the console
        print("\n" + "="*80)
        print(" [API RESPONSE] RESPUESTA GENERAL RECIBIDA DE OPEN-METEO")
        print("="*80)
        print(json.dumps(data, indent=2))
        print("="*80 + "\n")
        
        current = data.get("current", {})
        daily = data.get("daily", {})
        
        weather_info = {
            "time": current.get("time"),
            "temperature": current.get("temperature_2m"),
            "weather_code": current.get("weather_code"),
            "is_day": current.get("is_day"),
            "daily": daily,
            "raw": data
        }
        return weather_info
    except Exception as e:
        print(f"[Weather] Error al consultar datos del clima: {e}")
        return None

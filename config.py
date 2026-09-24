# WiFi & OTA Settings
WIFI_SSID = "El Fi del Wi"
WIFI_PASSWORD = "teamolionelscaloni"
WIFI_TIMEOUT_SECS = 20
OTA_BASE_URL = "https://raw.githubusercontent.com/ivanbudnick/Clima/master/"

# LED Hardware Settings
LED_PIN = 2
LED_COUNT = 6
FACTOR_BRILLO = 0.15
COLOR_ORDER = "RGB"

# Weather to LED Color Mapping
COLOR_MAPPINGS = {
    "CLEAR_DAY": (255, 180, 0),
    "CLEAR_NIGHT": (20, 30, 80),
    "CLOUDY": (100, 149, 237),
    "FOG": (120, 120, 140),
    "DRIZZLE": (75, 10, 130),
    "RAIN": (55, 0, 110),
    "SNOW": (240, 248, 255),
    "THUNDERSTORM": (80, 0, 140),
    "DEFAULT": (255, 255, 255)
}

REGIONS = {
    "actual": {"name": "Mi Ubicación Actual", "latitude": None, "longitude": None}
}

def get_weather_info(code, is_day=1):
    if code in (0, 1):
        key, desc = ("CLEAR_DAY", "Cielo Despejado (Día)") if is_day else ("CLEAR_NIGHT", "Cielo Despejado (Noche)")
    elif code in (2, 3):
        key, desc = "CLOUDY", "Nublado"
    elif code in (45, 48):
        key, desc = "FOG", "Niebla"
    elif 51 <= code <= 57:
        key, desc = "DRIZZLE", "Llovizna"
    elif (61 <= code <= 67) or (80 <= code <= 82):
        key, desc = "RAIN", "Lluvia Activa"
    elif (71 <= code <= 77) or (85 <= code <= 86):
        key, desc = "SNOW", "Nieve / Heladas"
    elif code in (95, 96, 99):
        key, desc = "THUNDERSTORM", "Tormenta Eléctrica"
    else:
        key, desc = "DEFAULT", "Condiciones Variables"

    return {
        "color_key": key,
        "led_color": COLOR_MAPPINGS.get(key, COLOR_MAPPINGS["DEFAULT"]),
        "description": desc
    }

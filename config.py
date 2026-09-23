# Configuration for Weather-based LED Strip Controller

# Wi-Fi Settings (used on MicroPython)
WIFI_SSID = "El Fi del Wi"
WIFI_PASSWORD = "teamolionelscaloni"
WIFI_TIMEOUT_SECS = 20

# OTA Update Settings (Base URL of raw files in the repository)
OTA_BASE_URL = "https://raw.githubusercontent.com/ivanbudnick/Clima/master/"

# Polling Settings (only used for standalone python loop)
POLL_INTERVAL_SECS = 900 

# LED Strip Settings
LED_PIN = 2
LED_COUNT = 6
FACTOR_BRILLO = 0.15  # Factor de brillo de seguridad (15%) por falta de capacitor
COLOR_ORDER = "RBG"   # Orden de color físico: "RGB", "GRB", "BRG" o "RBG"


# 8 Preset Regions (1 auto-detected, 7 representative locations)
REGIONS = {
    "actual": {
        "name": "Mi Ubicación Actual",
        "latitude": None,
        "longitude": None
    },
    "riad": {
        "name": "Riad, Arabia Saudita",
        "latitude": 24.7136,
        "longitude": 46.6753
    },
    "londres": {
        "name": "Londres, Reino Unido",
        "latitude": 51.5074,
        "longitude": -0.1278
    },
    "tromso": {
        "name": "Tromsø, Noruega",
        "latitude": 69.6492,
        "longitude": 18.9553
    },
    "manaos": {
        "name": "Manaos, Brasil",
        "latitude": -3.1190,
        "longitude": -60.0217
    },
    "sydney": {
        "name": "Sídney, Australia",
        "latitude": -33.8688,
        "longitude": 151.2093
    },
    "reikiavik": {
        "name": "Reikiavik, Islandia",
        "latitude": 64.1466,
        "longitude": -21.9426
    },
    "tokio": {
        "name": "Tokio, Japón",
        "latitude": 35.6762,
        "longitude": 139.6503
    }
}

# Weather to LED Color Mapping (RGB tuples: 0-255)
COLOR_MAPPINGS = {
    "CLEAR_DAY": (255, 180, 0),       # Warm Yellow/Orange
    "CLEAR_NIGHT": (20, 30, 80),       # Deep Dim Blue for night
    "CLOUDY": (100, 149, 237),         # Cornflower Blue / Grey-blue
    "FOG": (120, 120, 140),            # Misty Grey
    "DRIZZLE": (75, 10, 130),          # Indigo / Dark Violet
    "RAIN": (55, 0, 110),              # Deep Dark Violet
    "SNOW": (240, 248, 255),           # White / Alice Blue
    "THUNDERSTORM": (80, 0, 140),      # Dark Purple / Violet
    "DEFAULT": (255, 255, 255)         # White
}

# Webpage Background Colors (Pastel, desaturated, eye-friendly hex)
WEB_COLORS = {
    "CLEAR_DAY": "#FCF5E3",            # Soft warm amber
    "CLEAR_NIGHT": "#1D2330",          # Dark desaturated slate indigo (dark mode)
    "CLOUDY": "#E7EDF3",               # Calm slate grey
    "FOG": "#ECECEC",                  # Misty light grey
    "DRIZZLE": "#E4F6FD",              # Soft cyan
    "RAIN": "#DEE8F5",                 # Cool rain blue
    "SNOW": "#EDF7FA",                 # Soft snow white-blue
    "THUNDERSTORM": "#EDE6F7",         # Dim lavender-purple
    "DEFAULT": "#FFFFFF"               # Pure White
}

def get_weather_info(weather_code, is_day=1):
    """
    Translates WMO weather codes and day/night status into visual cues:
    Returns dict: {color_key, web_color, led_color, description}
    """
    if weather_code == 0:
        key = "CLEAR_DAY" if is_day else "CLEAR_NIGHT"
        desc = "Cielo Despejado (Día)" if is_day else "Cielo Despejado (Noche)"
    elif weather_code == 1:
        key = "CLEAR_DAY" if is_day else "CLEAR_NIGHT"
        desc = "Mayormente Despejado (Día)" if is_day else "Mayormente Despejado (Noche)"
    elif weather_code in [2, 3]:
        key = "CLOUDY"
        desc = "Parcialmente Nublado" if weather_code == 2 else "Nublado / Cubierto"
    elif weather_code in [45, 48]:
        key = "FOG"
        desc = "Presencia de Niebla"
    elif weather_code in [51, 53, 55, 56, 57]:
        key = "DRIZZLE"
        desc = "Llovizna Ligera"
    elif weather_code in [61, 63, 65, 66, 67, 80, 81, 82]:
        key = "RAIN"
        desc = "Lluvia Activa"
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        key = "SNOW"
        desc = "Nevadas / Heladas"
    elif weather_code in [95, 96, 99]:
        key = "THUNDERSTORM"
        desc = "Tormenta Eléctrica"
    else:
        key = "DEFAULT"
        desc = "Condiciones Variables"

    return {
        "color_key": key,
        "web_color": WEB_COLORS.get(key, WEB_COLORS["DEFAULT"]),
        "led_color": COLOR_MAPPINGS.get(key, COLOR_MAPPINGS["DEFAULT"]),
        "description": desc
    }

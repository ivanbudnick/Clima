import sys
import time
import config
import wifi_manager
from led_control import LEDController
import weather_client

def get_current_time_str():
    """
    Returns a simple timestamp string compatible with both standard Python and MicroPython.
    """
    try:
        # Standard Python
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except ImportError:
        # MicroPython local time (returns tuple)
        t = time.localtime()
        return f"{t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

def main():
    print("=" * 60)
    print("  INICIANDO CONTROLADOR DE TIRA LED BASADO EN EL CLIMA  ")
    print("=" * 60)
    print(f"Entorno: {'MicroPython' if wifi_manager.IS_MICROPYTHON else 'PC / Python Estándar'}")
    
    # 1. Connect to WiFi (no-op on PC)
    if not wifi_manager.connect_wifi(config.WIFI_SSID, config.WIFI_PASSWORD, config.WIFI_TIMEOUT_SECS):
        print("[Critical] Falló la conexión WiFi. Abortando.")
        return

    # 2. Initialize LED Controller
    leds = LEDController(config.LED_PIN, config.LED_COUNT)
    
    # 3. Detect Geolocation coordinates
    latitude, longitude = weather_client.get_location_coordinates()
    
    # 4. State tracking variables to optimize updates
    last_weather_code = None
    last_temperature = None
    first_run = True

    print(f"[Main] Iniciando bucle de consulta (Intervalo: {config.POLL_INTERVAL_SECS} segundos)...\n")

    # 5. Main Polling Loop
    while True:
        current_time = get_current_time_str()
        weather = weather_client.get_current_weather(latitude, longitude)
        
        if weather:
            temp = weather["temperature"]
            code = weather["weather_code"]
            
            # Check if weather data changed since last check (or if it's the first run)
            has_changed = (code != last_weather_code or temp != last_temperature)
            
            if has_changed or first_run:
                color_key = config.get_color_key(code)
                color = config.COLOR_MAPPINGS.get(color_key, config.COLOR_MAPPINGS["DEFAULT"])
                
                print(f"\n[{current_time}] 🌤️ ¡Actualización de Clima Detectada!")
                print(f"  - Temperatura: {temp}°C")
                print(f"  - Código de clima WMO: {code} (Categoría: {color_key})")
                
                # Update LED strip with the mapped color
                leds.set_color(*color)
                
                # Save state
                last_weather_code = code
                last_temperature = temp
                first_run = False
            else:
                # Heartbeat log to show script is active, without triggering LED or database updates
                print(f"[{current_time}] Comprobación: Sin cambios (Temp: {temp}°C, Código: {code}).")
        else:
            print(f"[{current_time}] ⚠️ No se pudo obtener la actualización del clima en este ciclo.")

        # Wait for the next check interval
        time.sleep(config.POLL_INTERVAL_SECS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Main] Programa detenido por el usuario. Apagando LEDs...")
        try:
            # Try to clear LEDs on exit if controller initialized
            leds = LEDController(config.LED_PIN, config.LED_COUNT)
            leds.clear()
        except:
            pass
        print("¡Adiós!")

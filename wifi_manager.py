import sys
import time

try:
    import network
    IS_MICROPYTHON = True
except ImportError:
    IS_MICROPYTHON = False

def connect_wifi(ssid, password, timeout=20):
    """
    Connects to WiFi if on MicroPython, or logs status if running on PC.
    Returns True if connected/on PC, False otherwise.
    """
    if not IS_MICROPYTHON:
        print("[WiFi] Ejecutando en PC: Usando conexión de red local existente.")
        return True

    print(f"[WiFi] Conectando a {ssid}...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print(f"[WiFi] Ya conectado. Info de red: {wlan.ifconfig()}")
        return True
        
    wlan.connect(ssid, password)
    
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("\n[WiFi] Error: Tiempo de espera agotado al conectar al WiFi.")
            return False
        print(".", end="")
        time.sleep(0.5)
        
    print(f"\n[WiFi] Conectado exitosamente! Info de red: {wlan.ifconfig()}")
    return True

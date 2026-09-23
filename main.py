import gc
import sys
import json
import time
import socket
import network

import config
import wifi_manager
from led_control import LEDController
import weather_client
import ota_updater

# Ejecutar recolección de basura inicial
gc.collect()

print("="*60)
print("  INICIANDO SERVIDOR DE CLIMA Y LEDS EN NODEMCU ESP8266  ")
print("="*60)

# 1. Conectar a la red Wi-Fi
print("[Main] Conectando a la red Wi-Fi...")
connected = wifi_manager.connect_wifi(config.WIFI_SSID, config.WIFI_PASSWORD, config.WIFI_TIMEOUT_SECS)
if not connected:
    print("\n" + "!"*60)
    print(" ERROR: No se pudo conectar al Wi-Fi.")
    print(" Por favor, configura tu SSID y Password correctos en config.py:")
    print("   WIFI_SSID = \"Tu_Red_WiFi\"")
    print("   WIFI_PASSWORD = \"Tu_Contrasena\"")
    print("!"*60 + "\n")
    sys.exit(1)

# 2. Inicializar controlador físico de NeoPixel
# En config.py definimos LED_PIN = 2 y LED_COUNT = 6
led_strip = LEDController(config.LED_PIN, config.LED_COUNT)
print(f"[Main] Controlador LED inicializado en GPIO {config.LED_PIN} con {config.LED_COUNT} píxeles.")

# --- HELPERS DEL SERVIDOR ---

def send_error(client_socket, status_code, message):
    """Envía un error HTTP de texto plano de manera limpia."""
    try:
        response = "HTTP/1.1 {} {}\r\n".format(status_code, message)
        response += "Content-Type: text/plain; charset=utf-8\r\n"
        response += "Connection: close\r\n\r\n"
        response += "Error {}: {}".format(status_code, message)
        client_socket.sendall(response.encode('utf-8'))
    except Exception as e:
        print("[Server] Error enviando respuesta 500/404: {}".format(e))

def send_file(client_socket, filepath, content_type):
    """Transmite un archivo en fragmentos de 1024 bytes para ahorrar RAM en el ESP8266."""
    try:
        with open(filepath, 'rb') as f:
            headers = "HTTP/1.1 200 OK\r\n"
            headers += "Content-Type: {}\r\n".format(content_type)
            headers += "Connection: close\r\n\r\n"
            client_socket.sendall(headers.encode('utf-8'))
            
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                client_socket.sendall(chunk)
                gc.collect()
    except OSError:
        # Fallback por si index.html está en la raíz en vez de templates/
        if "/" in filepath:
            fallback_path = filepath.split("/")[-1]
            try:
                with open(fallback_path, 'rb') as f:
                    headers = "HTTP/1.1 200 OK\r\n"
                    headers += "Content-Type: {}\r\n".format(content_type)
                    headers += "Connection: close\r\n\r\n"
                    client_socket.sendall(headers.encode('utf-8'))
                    while True:
                        chunk = f.read(1024)
                        if not chunk:
                            break
                        client_socket.sendall(chunk)
                        gc.collect()
                return
            except OSError:
                pass
        
        print("[Server] No se pudo encontrar el archivo: {}".format(filepath))
        send_error(client_socket, 404, "File Not Found")

def send_json(client_socket, data):
    """Codifica y envía un diccionario Python en formato JSON con cabeceras HTTP."""
    try:
        json_bytes = json.dumps(data).encode('utf-8')
        headers = "HTTP/1.1 200 OK\r\n"
        headers += "Content-Type: application/json; charset=utf-8\r\n"
        headers += "Content-Length: {}\r\n".format(len(json_bytes))
        headers += "Connection: close\r\n\r\n"
        client_socket.sendall(headers.encode('utf-8'))
        client_socket.sendall(json_bytes)
    except Exception as e:
        print("[Server] Error enviando JSON: {}".format(e))
        send_error(client_socket, 500, "Internal Server Error")

def parse_query(path):
    """Extrae el path base y un diccionario de parámetros de consulta (query params)."""
    if '?' in path:
        base_path, query_str = path.split('?', 1)
        params = {}
        for pair in query_str.split('&'):
            if '=' in pair:
                key, val = pair.split('=', 1)
                params[key] = val
            else:
                params[pair] = ''
        return base_path, params
    return path, {}

# --- INICIAR SOCKET TCP ---

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(2)

# Configurar polling no bloqueante para el socket
import uselect as select
poller = select.poll()
poller.register(s, select.POLLIN)

wlan = network.WLAN(network.STA_IF)
ip_address = wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0"

print("\n" + "="*60)
print(" SERVIDOR HTTP CORRIENDO EXITOSAMENTE")
print(" Abre tu navegador en: http://{}/".format(ip_address))
print("="*60 + "\n")

# Bucle principal del servidor HTTP
while True:
    client_sock = None
    try:
        gc.collect()
        led_strip.update()  # Actualizar frame de animación en los LEDs
        
        # Consultar si hay conexiones entrantes esperando (timeout de 20ms)
        events = poller.poll(20)
        if not events:
            continue
            
        client_sock, client_addr = s.accept()
        
        # Configurar un timeout corto para evitar bloqueos por sockets inactivos
        client_sock.settimeout(2.0)
        
        # Leer petición HTTP hasta el final de la cabecera (máx. 2048 bytes)
        req = b""
        while b"\r\n\r\n" not in req and len(req) < 2048:
            try:
                chunk = client_sock.recv(512)
                if not chunk:
                    break
                req += chunk
            except Exception:
                break
                
        if not req:
            client_sock.close()
            continue
            
        # Intentar decodificar la línea de petición
        try:
            req_line = req.decode('utf-8').split('\r\n')[0]
        except Exception:
            req_line = req.decode('latin-1').split('\r\n')[0]
            
        print("[Server] {} -> {}".format(client_addr[0], req_line))
        
        # Parsear método y ruta
        parts = req_line.split(' ')
        if len(parts) < 2:
            client_sock.close()
            continue
            
        method, full_path = parts[0], parts[1]
        base_path, params = parse_query(full_path)
        
        # --- ENRUTADOR ---
        
        if base_path == "/" or base_path == "/index.html":
            send_file(client_sock, "templates/index.html", "text/html")
            
        elif base_path == "/api/weather":
            # Extraer región elegida
            region_key = params.get("region", "actual")
            
            if region_key not in config.REGIONS:
                send_error(client_sock, 400, "Region invalida")
                client_sock.close()
                continue
                
            region_info = config.REGIONS[region_key]
            lat = region_info["latitude"]
            lon = region_info["longitude"]
            region_name = region_info["name"]
            
            try:
                # Si es ubicación actual y no tiene coordenadas asignadas, geolocaliza por IP pública
                if region_key == "actual" and (lat is None or lon is None):
                    lat, lon, detected_name = weather_client.get_location_coordinates()
                    region_name = "{} (Mi Ubicacion)".format(detected_name)
                    
                print("[Server] Buscando clima para '{}' ({}, {})...".format(region_name, lat, lon))
                
                weather_data = weather_client.get_current_weather(lat, lon)
                if not weather_data:
                    send_error(client_sock, 500, "Error obteniendo datos del clima")
                    client_sock.close()
                    continue
                    
                temp = weather_data["temperature"]
                code = weather_data["weather_code"]
                is_day = weather_data["is_day"]
                daily_forecast = weather_data.get("daily", {})
                raw_payload = weather_data["raw"]
                
                # Traducir a información visual (colores de la web y de la tira LED)
                visuals = config.get_weather_info(code, is_day)
                
                # Actualizar físicamente la tira LED con el color correspondiente y activar su animación
                led_color = visuals["led_color"]
                print("[Server] Configurando tira LED con animación para: {}".format(visuals["color_key"]))
                led_strip.set_mode(visuals["color_key"], led_color)
                
                # Responder JSON con los colores de simulación completos
                response_data = {
                    "region_key": region_key,
                    "region_name": region_name,
                    "temperature": temp,
                    "weather_code": code,
                    "is_day": is_day,
                    "description": visuals["description"],
                    "color_key": visuals["color_key"],
                    "web_color": visuals["web_color"],
                    "led_color": led_color,
                    "daily_forecast": daily_forecast,
                    "raw_payload": raw_payload
                }
                
                send_json(client_sock, response_data)
                
            except Exception as e:
                print("[Server] Error consultando el clima: {}".format(e))
                send_error(client_sock, 500, str(e))

        elif base_path == "/api/weather/custom":
            try:
                code = int(params.get("weather_code", "0"))
                is_day = int(params.get("is_day", "1"))
                temp = float(params.get("temperature", "22.0"))
                
                visuals = config.get_weather_info(code, is_day)
                
                r_val = params.get("r")
                g_val = params.get("g")
                b_val = params.get("b")
                
                if r_val is not None and g_val is not None and b_val is not None:
                    led_color = (int(r_val), int(g_val), int(b_val))
                else:
                    led_color = visuals["led_color"]
                    
                print("[Server] Custom preset/slider -> Code: {}, Day: {}, Temp: {} C, RGB: {}".format(code, is_day, temp, led_color))
                led_strip.set_mode(visuals["color_key"], led_color)
                
                response_data = {
                    "region_key": "custom",
                    "region_name": "Configuracion Personalizada",
                    "temperature": temp,
                    "weather_code": code,
                    "is_day": is_day,
                    "description": visuals["description"],
                    "color_key": visuals["color_key"],
                    "web_color": visuals["web_color"],
                    "led_color": led_color,
                    "raw_payload": {
                        "latitude": 0.0,
                        "longitude": 0.0,
                        "current_weather": {
                            "temperature": temp,
                            "weathercode": code,
                            "is_day": is_day,
                            "time": "Custom / Slider Override"
                        },
                        "custom_override": True,
                        "led_rgb": led_color
                    }
                }
                send_json(client_sock, response_data)
            except Exception as e:
                print("[Server] Error en /api/weather/custom: {}".format(e))
                send_error(client_sock, 500, str(e))
                
        elif base_path == "/api/ota/check":

            try:
                res = ota_updater.check_update(config.OTA_BASE_URL)
                send_json(client_sock, res)
            except Exception as e:
                send_json(client_sock, {"success": False, "error": str(e)})

        elif base_path == "/api/ota/update":
            try:
                success, msg = ota_updater.perform_ota_update(config.OTA_BASE_URL)
                send_json(client_sock, {"success": success, "message": msg})
                if success:
                    client_sock.close()
                    print("[Server] Reiniciando tras actualizacion en 2 segundos...")
                    time.sleep(2)
                    if ota_updater.IS_MICROPYTHON:
                        import machine
                        machine.reset()
                    else:
                        print("[Server] Entorno PC: Saliendo del proceso.")
                        sys.exit(0)
            except Exception as e:
                send_json(client_sock, {"success": False, "error": str(e)})
                
        else:
            send_error(client_sock, 404, "Not Found")
            
        client_sock.close()
        
    except Exception as e:
        print("[Server] Excepcion capturada: {}".format(e))
        if client_sock:
            try:
                client_sock.close()
            except Exception:
                pass
        time.sleep(0.5)

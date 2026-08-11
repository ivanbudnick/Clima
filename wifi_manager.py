import sys
import time
import json
import gc

try:
    import network
    IS_MICROPYTHON = True
except ImportError:
    IS_MICROPYTHON = False

CREDENTIALS_FILE = "wifi_credentials.json"

def load_credentials():
    """Carga las credenciales guardadas en el archivo wifi_credentials.json"""
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_credentials(ssid, password):
    """Guarda las credenciales de WiFi en wifi_credentials.json"""
    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({"ssid": ssid, "password": password}, f)
        print(f"[WiFi] Credenciales guardadas exitosamente para la red: {ssid}")
        return True
    except Exception as e:
        print(f"[WiFi] Error guardando credenciales: {e}")
        return False

def _connect_wifi_internal(ssid, password, timeout=20):
    """Lógica interna de conexión WiFi (solo MicroPython)"""
    if not IS_MICROPYTHON:
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

def get_setup_page(options):
    """Carga y procesa templates/setup.html o usa un fallback de texto plano"""
    try:
        with open("templates/setup.html", "r") as f:
            html = f.read()
        return html.replace("{networks_options}", options)
    except Exception as e:
        print(f"[WiFi] No se pudo leer templates/setup.html: {e}. Usando fallback.")
        return f"""<!DOCTYPE html><html><body>
        <h1>Configurar Wi-Fi (Modo Fallback)</h1>
        <form action="/save" method="GET">
        SSID: <select name="ssid">{options}<option value="__manual__">-- Manual --</option></select><br>
        SSID Manual: <input type="text" name="manual_ssid"><br>
        Contraseña: <input type="password" name="password"><br>
        <button type="submit">Conectar</button>
        </form></body></html>"""

def start_setup_portal():
    """Inicia el Punto de Acceso y el Servidor HTTP de configuración."""
    if not IS_MICROPYTHON:
        print("[WiFi] Ejecutando en PC: Portal de configuración omitido.")
        return False

    print("\n" + "="*60)
    print(" INICIANDO MODO DE CONFIGURACIÓN AP Y PORTAL CAUTIVO")
    print("="*60)

    # 1. Configurar AP (Access Point)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="Clima-LED-Setup", password="") # Red abierta
    
    # 2. Escanear redes disponibles con STA_IF
    networks_list = []
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        raw_nets = wlan.scan()
        seen = set()
        for net in raw_nets:
            ssid_name = net[0].decode('utf-8', 'ignore').strip()
            if ssid_name and ssid_name not in seen:
                seen.add(ssid_name)
                networks_list.append(ssid_name)
    except Exception as e:
        print(f"[WiFi] Error al escanear redes: {e}")

    if networks_list:
        options = "\n".join([f'<option value="{n}">{n}</option>' for n in networks_list])
    else:
        options = '<option value="">Ninguna red detectada automáticamente</option>'

    ap_ip = ap.ifconfig()[0]
    print(f"[WiFi] Punto de acceso iniciado: 'Clima-LED-Setup'")
    print(f"[WiFi] Por favor conéctate a esta red y abre en tu navegador: http://{ap_ip}/")
    print("="*60 + "\n")

    # 3. Iniciar socket del servidor
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(1)

    save_received = False
    new_ssid = ""
    new_password = ""

    while not save_received:
        client_sock = None
        try:
            gc.collect()
            client_sock, client_addr = s.accept()
            client_sock.settimeout(2.0)
            
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

            try:
                req_str = req.decode('utf-8', 'ignore')
            except Exception:
                req_str = req.decode('latin-1', 'ignore')

            req_line = req_str.split('\r\n')[0]
            print(f"[WiFi Portal] {client_addr[0]} -> {req_line}")

            parts = req_line.split(' ')
            if len(parts) < 2:
                client_sock.close()
                continue

            method, path = parts[0], parts[1]

            if "/save" in path:
                # Extraer parámetros de consulta
                query = path.split('?')[1] if '?' in path else ''
                params = {}
                for pair in query.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        # Decodificar URL-encoding simple (%20, +)
                        v = v.replace('+', ' ')
                        v = v.replace('%20', ' ')
                        v = v.replace('%21', '!')
                        v = v.replace('%40', '@')
                        v = v.replace('%23', '#')
                        v = v.replace('%24', '$')
                        v = v.replace('%25', '%')
                        v = v.replace('%2A', '*')
                        params[k] = v
                
                ssid_param = params.get('ssid', '')
                manual_ssid = params.get('manual_ssid', '')
                password_param = params.get('password', '')

                selected_ssid = manual_ssid if ssid_param == '__manual__' else ssid_param
                if selected_ssid:
                    new_ssid = selected_ssid
                    new_password = password_param
                    save_received = True

                    save_credentials(new_ssid, new_password)

                    # Responder éxito
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
                    success_html = f"""<!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Guardado</title>
                        <style>
                            body {{ font-family: sans-serif; background: #f3f4f6; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
                            .card {{ background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
                            h2 {{ color: #10B981; }}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h2>✓ Configuración Guardada</h2>
                            <p>Reiniciando la estación... Conéctate a tu red habitual <b>{new_ssid}</b> para ver el panel de control.</p>
                        </div>
                    </body>
                    </html>"""
                    client_sock.sendall(response.encode('utf-8') + success_html.encode('utf-8'))
                else:
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nError: SSID no proporcionado."
                    client_sock.sendall(response.encode('utf-8'))
            else:
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
                page_html = get_setup_page(options)
                client_sock.sendall(response.encode('utf-8') + page_html.encode('utf-8'))

            client_sock.close()
        except Exception as e:
            print(f"[WiFi Portal] Error: {e}")
            if client_sock:
                try:
                    client_sock.close()
                except Exception:
                    pass

    s.close()
    print("[WiFi] Credenciales recibidas. Reiniciando dispositivo en 2 segundos...")
    time.sleep(2)
    
    import machine
    machine.reset()

def connect_wifi(ssid, password, timeout=20):
    """
    Intenta conectar al WiFi usando credenciales locales dinámicas o de configuración.
    Si falla, inicia el portal cautivo en Punto de Acceso (AP).
    """
    if not IS_MICROPYTHON:
        print("[WiFi] Ejecutando en PC: Usando conexión de red local existente.")
        return True

    # Cargar credenciales guardadas si existen
    saved = load_credentials()
    if saved:
        ssid = saved.get("ssid", ssid)
        password = saved.get("password", password)
        print(f"[WiFi] Usando credenciales dinámicas guardadas para: {ssid}")

    connected = _connect_wifi_internal(ssid, password, timeout)
    if not connected:
        start_setup_portal()
        return False
        
    return True

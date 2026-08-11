import json
import gc
import sys

try:
    import urequests as requests
    IS_MICROPYTHON = True
except ImportError:
    import requests
    IS_MICROPYTHON = False

CREDENTIALS_FILE = "wifi_credentials.json"
VERSION_FILE = "version.json"

FILES_TO_UPDATE = [
    "version.json",
    "main.py",
    "config.py",
    "wifi_manager.py",
    "weather_client.py",
    "led_control.py",
    "templates/index.html",
    "templates/setup.html"
]

def read_local_version():
    """Lee la versión actual del archivo version.json local."""
    try:
        with open(VERSION_FILE, "r") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception:
        return "0.0.0"

def compare_versions(v1, v2):
    """Compara v1 y v2. Retorna True si v2 > v1."""
    try:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        # Rellenar con ceros si tienen distinta longitud
        max_len = max(len(parts1), len(parts2))
        parts1 += [0] * (max_len - len(parts1))
        parts2 += [0] * (max_len - len(parts2))
        return parts2 > parts1
    except Exception:
        return v2 != v1

def check_update(base_url):
    """Consulta la versión remota y la compara con la local."""
    url = base_url + "version.json"
    print(f"[OTA] Consultando versión remota en: {url}")
    response = None
    try:
        # En PC usamos timeout
        if IS_MICROPYTHON:
            response = requests.get(url)
        else:
            response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            remote_version = data.get("version", "0.0.0")
            local_version = read_local_version()
            update_available = compare_versions(local_version, remote_version)
            
            print(f"[OTA] Versión Local: {local_version} | Versión Remota: {remote_version}")
            return {
                "success": True,
                "update_available": update_available,
                "local_version": local_version,
                "remote_version": remote_version
            }
        else:
            print(f"[OTA] Error al consultar versión remota. Status: {response.status_code}")
            return {"success": False, "error": f"HTTP status {response.status_code}"}
    except Exception as e:
        print(f"[OTA] Error consultando versión remota: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if response:
            try:
                response.close()
            except Exception:
                pass
        gc.collect()

def ensure_dir(path):
    """Asegura que el directorio del archivo exista antes de abrirlo."""
    import os
    if "/" in path:
        parts = path.split("/")
        current = ""
        for p in parts[:-1]:
            current = current + "/" + p if current else p
            try:
                os.mkdir(current)
            except OSError:
                pass

def perform_ota_update(base_url):
    """
    Descarga todos los archivos como .tmp de forma fragmentada para ahorrar RAM.
    Si todo tiene éxito, reemplaza los archivos antiguos y retorna True.
    """
    import os
    print(f"[OTA] Iniciando proceso de descarga desde: {base_url}")
    downloaded_files = []
    
    gc.collect()
    
    for filename in FILES_TO_UPDATE:
        url = base_url + filename
        target_path = filename
        
        ensure_dir(target_path)
        
        success = False
        response = None
        try:
            if IS_MICROPYTHON:
                response = requests.get(url)
            else:
                response = requests.get(url, stream=True)
                
            if response.status_code == 200:
                with open(target_path + ".tmp", "wb") as f:
                    if IS_MICROPYTHON:
                        while True:
                            chunk = response.raw.read(512)
                            if not chunk:
                                break
                            f.write(chunk)
                    else:
                        for chunk in response.iter_content(chunk_size=512):
                            if chunk:
                                f.write(chunk)
                success = True
                downloaded_files.append(target_path)
                print(f"[OTA] Descargado con éxito: {filename}")
            else:
                print(f"[OTA] Error de descarga (Status {response.status_code}): {filename}")
            
            if response:
                response.close()
        except Exception as e:
            print(f"[OTA] Excepción descargando {filename}: {e}")
            if response:
                try:
                    response.close()
                except Exception:
                    pass
        
        gc.collect()
        
        if not success:
            # Fallo: abortar y borrar archivos temporales creados para evitar basura
            print("[OTA] Abortando actualización y limpiando temporales...")
            for fp in downloaded_files:
                try:
                    os.remove(fp + ".tmp")
                except OSError:
                    pass
            return False, f"Fallo al descargar {filename}"
            
    # Reemplazar archivos finales
    print("[OTA] Aplicando nuevos archivos...")
    for fp in downloaded_files:
        try:
            try:
                os.remove(fp)
            except OSError:
                pass
            os.rename(fp + ".tmp", fp)
            print(f"[OTA] Actualizado: {fp}")
        except Exception as e:
            print(f"[OTA] Error aplicando {fp}: {e}")
            return False, f"Error al aplicar archivo {fp}"
            
    print("[OTA] Actualización completada con éxito.")
    return True, "Actualización exitosa"

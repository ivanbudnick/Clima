import os
import sys
from flask import Flask, render_template, request, jsonify
import config
from led_control import LEDController
import weather_client

app = Flask(__name__)

# Initialize a persistent global LED controller
# (On PC, this simulates the strip; on MicroPython, it drives the physical GPIO)
led_strip = LEDController(config.LED_PIN, config.LED_COUNT)

@app.route("/")
def home():
    """
    Renders the main dashboard page.
    """
    return render_template("index.html")

@app.route("/api/weather")
def api_weather():
    """
    API endpoint: /api/weather?region=<region_key>
    Fetches coordinates for the region, calls Open-Meteo, logs raw API output,
    updates the LED strip, and returns visual specs.
    """
    region_key = request.args.get("region", "actual")
    
    if region_key not in config.REGIONS:
        return jsonify({"error": "Región inválida"}), 400
        
    region_info = config.REGIONS[region_key]
    lat = region_info["latitude"]
    lon = region_info["longitude"]
    region_name = region_info["name"]
    
    try:
        if region_key == "actual" and (lat is None or lon is None):
            lat, lon, detected_name = weather_client.get_location_coordinates()
            region_name = f"{detected_name} (Mi Ubicación)"
            
        print(f"[Backend] Consultado clima para '{region_name}' ({lat}, {lon})...")
        
        # 2. Query Open-Meteo
        weather_data = weather_client.get_current_weather(lat, lon)
        if not weather_data:
            return jsonify({"error": "No se pudo obtener datos del clima"}), 500
            
        temp = weather_data["temperature"]
        code = weather_data["weather_code"]
        is_day = weather_data["is_day"]
        raw_payload = weather_data["raw"]
        
        # 3. Translate climate code into web and LED colors
        visuals = config.get_weather_info(code, is_day)
        
        # 4. Update the LED strip
        led_color = visuals["led_color"]
        led_strip.set_color(*led_color)
        
        # 5. Build and return JSON response
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
            "raw_payload": raw_payload
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[Backend] Error en api_weather: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run server locally on port 5000
    print("=" * 60)
    print("  SERVIDOR WEB DEL CLIMA Y CONTROL LED INICIADO  ")
    print("  Abre en tu navegador: http://localhost:5001    ")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5001, debug=True)

import time
import machine
import neopixel
import config

print("=" * 60)
print("  TEST DE PRIMEROS 5 LEDs (5 SEGUNDOS POR COLOR)  ")
print("=" * 60)

# Configuración del test
pin_num = getattr(config, 'LED_PIN', 2)
TEST_LEDS = 5        # Probar solo los primeros 5 píxeles
TOTAL_LEDS = 25      # Enviar apagado al resto de la tira para limpiar ruido
factor = getattr(config, 'FACTOR_BRILLO', 0.15)
order = getattr(config, 'COLOR_ORDER', 'RGB')

print(f"[Configuración] Orden de Color: {order} | Pin: GPIO {pin_num} | Probando primeros: {TEST_LEDS} LEDs | Brillo: {int(factor*100)}% | Tiempo: 5s por color\n")

pin = machine.Pin(pin_num, machine.Pin.OUT)
np = neopixel.NeoPixel(pin, TOTAL_LEDS)

def mostrar_color(nombre, r, g, b):
    print(f"[{time.ticks_ms()//1000}s] RGB Solicitado: ({r:3d}, {g:3d}, {b:3d})  -->  Mostrando: {nombre}")
    r_adj = int(r * factor)
    g_adj = int(g * factor)
    b_adj = int(b * factor)
    
    # Prepara la tupla según el orden físico (GRB por defecto)
    if order == 'GRB':
        color_pixel = (g_adj, r_adj, b_adj)
    elif order == 'BRG':
        color_pixel = (b_adj, r_adj, g_adj)
    elif order == 'RBG':
        color_pixel = (r_adj, b_adj, g_adj)
    else: # RGB
        color_pixel = (r_adj, g_adj, b_adj)

    # 1. Los primeros 5 LEDs toman el color de prueba
    for i in range(TEST_LEDS):
        np[i] = color_pixel
        
    # 2. El resto de los LEDs de la tira se apagan para evitar parpadeos/ruido
    for i in range(TEST_LEDS, TOTAL_LEDS):
        np[i] = (0, 0, 0)
        
    np.write()

# Secuencia de prueba ordenada
colores_test = [
    ("ROJO PURO", 255, 0, 0),
    ("VERDE PURO", 0, 255, 0),
    ("AZUL PURO", 0, 0, 255),
    ("AMARILLO", 255, 255, 0),
    ("CIAN / AZUL CLARO", 0, 255, 255),
    ("MAGENTA / ROSA", 255, 0, 255),
    ("BLANCO", 255, 255, 255),
    ("APAGADO", 0, 0, 0)
]

try:
    while True:
        print("\n--- Iniciando ciclo (5 segundos por color) ---")
        for nombre, r, g, b in colores_test:
            mostrar_color(nombre, r, g, b)
            time.sleep(5)  # 5 segundos por color
except KeyboardInterrupt:
    print("\nPrueba detenida. Apagando LEDs...")
    mostrar_color("APAGADO", 0, 0, 0)

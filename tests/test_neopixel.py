import machine
import neopixel
import time
import random

# --- CONFIGURACIÓN ---
PIN_DATOS = 2
CANTIDAD_PIXELES = 6  # Tira recortada a 6 unidades lógicas (18 LEDs físicos)
FACTOR_BRILLO = 0.25   # 25% de brillo para proteger la protoboard

pin = machine.Pin(PIN_DATOS, machine.Pin.OUT)
np = neopixel.NeoPixel(pin, CANTIDAD_PIXELES)

# --- UTILIDADES DE COLOR ---
def aplicar_brillo(r, g, b):
    """Aplica el factor de brillo global a un color RGB."""
    return (int(r * FACTOR_BRILLO), int(g * FACTOR_BRILLO), int(b * FACTOR_BRILLO))

def apagar():
    """Apaga todos los píxeles."""
    for i in range(CANTIDAD_PIXELES):
        np[i] = (0, 0, 0)
    np.write()

def wheel(pos):
    """Genera colores de transición (arcoíris) en base a un valor de 0 a 255."""
    pos = pos & 255
    if pos < 85:
        return aplicar_brillo(255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return aplicar_brillo(0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return aplicar_brillo(pos * 3, 0, 255 - pos * 3)

# --- 1. EXPANSIÓN Y CONTRACCIÓN (Desde el centro hacia afuera) ---
def expansion_contraccion(espera=0.15, repeticiones=8):
    print("-> Ejecutando: Expansión y Contracción ↔️")
    # Centros de una tira de 6: índices 2 y 3
    secuencia = [
        (2, 3), # Centro
        (1, 4), # Medio
        (0, 5)  # Extremos
    ]
    
    color_offset = 0
    for _ in range(repeticiones):
        color_offset += 25  # Cambia el tono en cada ciclo
        
        # Fase de expansión (afuera)
        for paso, pixeles in enumerate(secuencia):
            for i in range(CANTIDAD_PIXELES):
                np[i] = (0, 0, 0) # Apagar todo
            
            # Encender el par correspondiente con color arcoíris
            c = wheel(color_offset + paso * 40)
            np[pixeles[0]] = c
            np[pixeles[1]] = c
            np.write()
            time.sleep(espera)
            
        # Fase de contracción (adentro)
        for paso, pixeles in enumerate(reversed(secuencia[1:-1])):
            for i in range(CANTIDAD_PIXELES):
                np[i] = (0, 0, 0)
                
            c = wheel(color_offset + (2 - paso) * 40)
            np[pixeles[0]] = c
            np[pixeles[1]] = c
            np.write()
            time.sleep(espera)

# --- 2. ONDA ALTERNADA CON CROSS-FADE (Pares vs Impares) ---
def onda_alternada(espera=0.03, ciclos=6):
    print("-> Ejecutando: Alternancia de Pares e Impares 🔀")
    pasos = 30 # Pasos de desvanecimiento
    
    color_base = 0
    for _ in range(ciclos):
        color_base += 40
        c1 = wheel(color_base)
        c2 = wheel(color_base + 128) # Color complementario en el círculo cromático
        
        # Transición: Pares se encienden, Impares se apagan
        for p in range(pasos):
            factor_pares = p / pasos
            factor_impares = 1.0 - factor_pares
            
            for i in range(CANTIDAD_PIXELES):
                if i % 2 == 0:
                    # Pares aumentando
                    np[i] = (int(c1[0] * factor_pares), int(c1[1] * factor_pares), int(c1[2] * factor_pares))
                else:
                    # Impares disminuyendo
                    np[i] = (int(c2[0] * factor_impares), int(c2[1] * factor_impares), int(c2[2] * factor_impares))
            np.write()
            time.sleep(espera)
            
        # Transición inversa: Impares se encienden, Pares se apagan
        for p in range(pasos):
            factor_impares = p / pasos
            factor_pares = 1.0 - factor_impares
            
            for i in range(CANTIDAD_PIXELES):
                if i % 2 == 0:
                    # Pares disminuyendo
                    np[i] = (int(c1[0] * factor_pares), int(c1[1] * factor_pares), int(c1[2] * factor_pares))
                else:
                    # Impares aumentando
                    np[i] = (int(c2[0] * factor_impares), int(c2[1] * factor_impares), int(c2[2] * factor_impares))
            np.write()
            time.sleep(espera)

# --- 3. REBOTE ARCOÍRIS CON COLA DE COLOR (KITT mejorado) ---
def rebote_color(espera=0.06, vueltas=6):
    print("-> Ejecutando: Rebote con Estela de Color 🔴🟠🟡")
    pos_color = 0
    
    for _ in range(vueltas):
        # Ida
        for i in range(CANTIDAD_PIXELES):
            pos_color += 8 # Va rotando el color en cada paso
            color_principal = wheel(pos_color)
            color_cola = wheel(pos_color - 30)
            
            # Limpiamos el buffer
            for j in range(CANTIDAD_PIXELES):
                np[j] = (0, 0, 0)
                
            if i > 0:
                # Estela (pixel anterior atenuado)
                np[i-1] = (int(color_cola[0]*0.25), int(color_cola[1]*0.25), int(color_cola[2]*0.25))
            np[i] = color_principal
            np.write()
            time.sleep(espera)
            
        # Vuelta
        for i in range(CANTIDAD_PIXELES - 1, -1, -1):
            pos_color += 8
            color_principal = wheel(pos_color)
            color_cola = wheel(pos_color - 30)
            
            for j in range(CANTIDAD_PIXELES):
                np[j] = (0, 0, 0)
                
            if i < CANTIDAD_PIXELES - 1:
                # Estela (pixel de la derecha ahora)
                np[i+1] = (int(color_cola[0]*0.25), int(color_cola[1]*0.25), int(color_cola[2]*0.25))
            np[i] = color_principal
            np.write()
            time.sleep(espera)

# --- 4. BARRIDO LLENADO / VACIADO ---
def barrido_acumulativo(espera=0.1, repeticiones=4):
    print("-> Ejecutando: Llenado y Vaciado Acumulativo 🔋")
    color_base = 0
    
    for _ in range(repeticiones):
        color_base += 60
        color_actual = wheel(color_base)
        
        # 1. Llenamos píxel por píxel de izquierda a derecha
        for i in range(CANTIDAD_PIXELES):
            np[i] = color_actual
            np.write()
            time.sleep(espera)
            
        # 2. Vaciamos píxel por píxel de derecha a izquierda
        for i in range(CANTIDAD_PIXELES - 1, -1, -1):
            np[i] = (0, 0, 0)
            np.write()
            time.sleep(espera)

# --- 5. PERSECUCIÓN DE CHISPAS (Spark Chase) ---
def chispa_perseguidora(espera=0.08, vueltas=6):
    print("-> Ejecutando: Chispa Perseguidora ✨")
    # Genera un fondo suave que cambia de color lentamente
    color_ciclo = 0
    for _ in range(vueltas):
        for i in range(CANTIDAD_PIXELES):
            color_ciclo += 5
            c_fondo = wheel(color_ciclo)
            # Fondo muy apagado
            r_bg, g_bg, b_bg = int(c_fondo[0]*0.05), int(c_fondo[1]*0.05), int(c_fondo[2]*0.05)
            
            # Pintamos fondo
            for j in range(CANTIDAD_PIXELES):
                np[j] = (r_bg, g_bg, b_bg)
            
            # Colocamos una "chispa" blanca brillante en la posición actual
            np[i] = aplicar_brillo(255, 255, 255)
            # Y un destello de color en los adyacentes
            if i > 0:
                np[i-1] = wheel(color_ciclo + 100)
            if i < CANTIDAD_PIXELES - 1:
                np[i+1] = wheel(color_ciclo + 100)
                
            np.write()
            time.sleep(espera)

# --- LOOP PRINCIPAL ---
try:
    print("Iniciando animaciones para tira corta (6 píxeles)...")
    apagar()
    
    while True:
        # Ejecuta la secuencia de patrones
        expansion_contraccion(espera=0.15, repeticiones=8)
        apagar()
        time.sleep(0.4)
        
        onda_alternada(espera=0.02, ciclos=4)
        apagar()
        time.sleep(0.4)
        
        rebote_color(espera=0.06, vueltas=5)
        apagar()
        time.sleep(0.4)
        
        barrido_acumulativo(espera=0.08, repeticiones=4)
        apagar()
        time.sleep(0.4)
        
        chispa_perseguidora(espera=0.07, vueltas=5)
        apagar()
        time.sleep(0.4)

except KeyboardInterrupt:
    print("\nPrograma detenido. Apagando tira LED...")
    apagar()

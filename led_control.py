import sys
import config
import time

try:
    import urandom
    HAS_URANDOM = True
except ImportError:
    import random
    HAS_URANDOM = False

def get_random():
    if HAS_URANDOM:
        return urandom.getrandbits(10) / 1024.0
    else:
        return random.random()

try:
    import machine
    import neopixel
    IS_MICROPYTHON = True
except ImportError:
    IS_MICROPYTHON = False

class LEDController:
    def __init__(self, pin_num, led_count):
        self.pin_num = pin_num
        self.led_count = led_count
        self.current_color = (0, 0, 0)
        self.current_physical = (0, 0, 0)  # R, G, B atenuados físicos actuales
        self.mode = "STATIC"               # Modos: "STATIC", "CLEAR_DAY", "RAIN", etc.
        self.last_tick = 0
        self.step_counter = 0
        
        # Estados independientes para la animación de titilación por píxel
        # 0 = Reposo, > 0 = Ciclo de flash, < 0 = Ciclo de atenuación/gota
        self.pixel_states = [0] * led_count
        
        if IS_MICROPYTHON:
            # On MicroPython, initialize the physical NeoPixel strip
            pin = machine.Pin(pin_num, machine.Pin.OUT)
            self.np = neopixel.NeoPixel(pin, led_count)
            self.clear()
        else:
            self.np = None
            print(f"[LED Simulator] Inicializado con {led_count} LEDs (Simulado en Pin GPIO {pin_num}).")
            self.clear()

    def set_color(self, r, g, b):
        """Aplica un color estático de forma instantánea y detiene las animaciones."""
        self.current_color = (r, g, b)
        self.mode = "STATIC"
        self.pixel_states = [0] * self.led_count
        
        if IS_MICROPYTHON:
            factor = getattr(config, 'FACTOR_BRILLO', 0.15)
            r_target = int(r * factor)
            g_target = int(g * factor)
            b_target = int(b * factor)
            
            order = getattr(config, 'COLOR_ORDER', 'RBG')
            for i in range(self.led_count):
                if order == 'GRB':
                    self.np[i] = (g_target, r_target, b_target)
                elif order == 'BRG':
                    self.np[i] = (b_target, r_target, g_target)
                elif order == 'RBG':
                    self.np[i] = (r_target, b_target, g_target)
                else:
                    self.np[i] = (r_target, g_target, b_target)
            self.np.write()
            self.current_physical = (r_target, g_target, b_target)
        else:
            self._simulate_print(r, g, b)

    def set_mode(self, mode_name, rgb):
        """Configura el modo de animación y realiza una transición suave hacia el nuevo color base."""
        self.mode = mode_name
        self.current_color = rgb
        self.pixel_states = [0] * self.led_count  # Resetear estados de animación
        self.fade_to(rgb[0], rgb[1], rgb[2])

    def fade_to(self, r, g, b):
        """Transición progresiva en 15 pasos para suavizar la corriente y evitar caídas de tensión."""
        if IS_MICROPYTHON:
            factor = getattr(config, 'FACTOR_BRILLO', 0.15)
            r_target = int(r * factor)
            g_target = int(g * factor)
            b_target = int(b * factor)
            
            r_start, g_start, b_start = self.current_physical
            order = getattr(config, 'COLOR_ORDER', 'RBG')
            
            steps = 15
            for step in range(1, steps + 1):
                r_curr = int(r_start + (r_target - r_start) * step / steps)
                g_curr = int(g_start + (g_target - g_start) * step / steps)
                b_curr = int(b_start + (b_target - b_start) * step / steps)
                
                for i in range(self.led_count):
                    if order == 'GRB':
                        self.np[i] = (g_curr, r_curr, b_curr)
                    elif order == 'BRG':
                        self.np[i] = (b_curr, r_curr, g_curr)
                    elif order == 'RBG':
                        self.np[i] = (r_curr, b_curr, g_curr)
                    else:
                        self.np[i] = (r_curr, g_curr, b_curr)
                self.np.write()
                time.sleep_ms(10)
                
            self.current_physical = (r_target, g_target, b_target)
        else:
            self._simulate_print(r, g, b)

    def update(self):
        """Actualiza el frame de animación según el modo activo. Llamado en el bucle principal del servidor."""
        if not IS_MICROPYTHON or self.mode == "STATIC":
            return
            
        now = time.ticks_ms()
        # Actualizar animación cada 50ms (~20 FPS) para que se sienta fluida
        if time.ticks_diff(now, self.last_tick) < 50:
            return
        self.last_tick = now
        
        factor = getattr(config, 'FACTOR_BRILLO', 0.15)
        order = getattr(config, 'COLOR_ORDER', 'RBG')
        
        if self.mode in ("RAIN", "DRIZZLE", "THUNDERSTORM"):
            # Lluvia / Tormenta: Tono violeta oscuro con titileo dinámico independiente por unidad
            r_base, g_base, b_base = self.current_color
            
            # Aplicar factor de brillo base
            r_phys = int(r_base * factor)
            g_phys = int(g_base * factor)
            b_phys = int(b_base * factor)
            
            for i in range(self.led_count):
                state = self.pixel_states[i]
                
                # Si el píxel está en reposo, tiene chance de iniciar un nuevo ciclo
                if state == 0:
                    rand = get_random()
                    if rand < 0.02:
                        # Inicia ciclo de flash rápido (3 frames de duración)
                        self.pixel_states[i] = 3
                        state = 3
                    elif rand < 0.09:
                        # Inicia ciclo de atenuación/gota cayendo (5 frames de duración)
                        self.pixel_states[i] = -5
                        state = -5
                
                # Procesar el estado de este píxel
                if state > 0:
                    # Flash: Brillo alto transitorio e inyección de blanco-celeste
                    mult = 1.0 + (1.5 * state / 3)
                    r_curr = min(255, int(r_phys * mult + (40 * state)))
                    g_curr = min(255, int(g_phys * mult + (20 * state)))
                    b_curr = min(255, int(b_phys * mult + (40 * state)))
                    self.pixel_states[i] -= 1
                elif state < 0:
                    # Gota / atenuación: Cae rápido a 10% de brillo y se recupera linealmente hacia 0
                    mult = 0.1 + 0.9 * (5 + state) / 5.0
                    r_curr = int(r_phys * mult)
                    g_curr = int(g_phys * mult)
                    b_curr = int(b_phys * mult)
                    self.pixel_states[i] += 1
                else:
                    # Reposo: Violeta oscuro estable
                    r_curr, g_curr, b_curr = r_phys, g_phys, b_phys
                
                # Escribir canal mapeado
                if order == 'GRB':
                    self.np[i] = (g_curr, r_curr, b_curr)
                elif order == 'BRG':
                    self.np[i] = (b_curr, r_curr, g_curr)
                elif order == 'RBG':
                    self.np[i] = (r_curr, b_curr, g_curr)
                else:
                    self.np[i] = (r_curr, g_curr, b_curr)
            self.np.write()
            
        elif self.mode == "CLEAR_DAY":
            # Soleado: Gradiente cálido de amarillos y naranjas que respira lentamente
            self.step_counter = (self.step_counter + 1) % 80
            # Oscilación de brillo lenta y muy marcada (de 0.45 a 1.0)
            if self.step_counter < 40:
                breath = 0.45 + (0.55 * self.step_counter / 40)
            else:
                breath = 0.45 + (0.55 * (80 - self.step_counter) / 40)
                
            pixel_factor = factor * breath
            
            # Gradiente de sol (desde naranja rojizo a amarillo brillante)
            gradient_colors = [
                (255, 110, 0),   # Naranja fuerte
                (255, 160, 0),   # Amarillo-Naranja
                (255, 205, 0),   # Amarillo sol
                (255, 225, 0),   # Amarillo brillante
                (255, 175, 0),   # Amarillo cálido
                (255, 120, 0)    # Naranja cálido
            ]
            
            for i in range(self.led_count):
                r_base, g_base, b_base = gradient_colors[i % len(gradient_colors)]
                r_curr = int(r_base * pixel_factor)
                g_curr = int(g_base * pixel_factor)
                b_curr = int(b_base * pixel_factor)
                
                if order == 'GRB':
                    self.np[i] = (g_curr, r_curr, b_curr)
                elif order == 'BRG':
                    self.np[i] = (b_curr, r_curr, g_curr)
                elif order == 'RBG':
                    self.np[i] = (r_curr, b_curr, g_curr)
                else:
                    self.np[i] = (r_curr, g_curr, b_curr)
            self.np.write()
            
        elif self.mode == "CLEAR_NIGHT":
            # Noche despejada: Azul profundo con centelleo estelar lento
            r_base, g_base, b_base = self.current_color
            r_phys = int(r_base * factor)
            g_phys = int(g_base * factor)
            b_phys = int(b_base * factor)
            
            for i in range(self.led_count):
                state = self.pixel_states[i]
                
                if state == 0:
                    rand = get_random()
                    if rand < 0.015:
                        self.pixel_states[i] = 10 # Ciclo de centelleo largo
                        state = 10
                
                if state > 0:
                    # Centelleo: oscilación senoidal aproximada de brillo
                    # va de 10 a 1
                    mult = 1.0 + 0.6 * (state - 5) / 5.0  # Oscila entre 0.4x y 1.6x
                    r_curr = max(0, min(255, int(r_phys * mult)))
                    g_curr = max(0, min(255, int(g_phys * mult)))
                    b_curr = max(0, min(255, int(b_phys * mult)))
                    self.pixel_states[i] -= 1
                else:
                    r_curr, g_curr, b_curr = r_phys, g_phys, b_phys
                    
                if order == 'GRB':
                    self.np[i] = (g_curr, r_curr, b_curr)
                elif order == 'BRG':
                    self.np[i] = (b_curr, r_curr, g_curr)
                elif order == 'RBG':
                    self.np[i] = (r_curr, b_curr, g_curr)
                else:
                    self.np[i] = (r_curr, g_curr, b_curr)
            self.np.write()
            
        else:
            # Otros modos (CLOUDY, FOG, SNOW, etc.): Respiración monocromática marcada (0.45 a 1.0)
            self.step_counter = (self.step_counter + 1) % 60
            if self.step_counter < 30:
                breath = 0.45 + (0.55 * self.step_counter / 30)
            else:
                breath = 0.45 + (0.55 * (60 - self.step_counter) / 30)
                
            pixel_factor = factor * breath
            r_base, g_base, b_base = self.current_color
            r_curr = int(r_base * pixel_factor)
            g_curr = int(g_base * pixel_factor)
            b_curr = int(b_base * pixel_factor)
            
            for i in range(self.led_count):
                if order == 'GRB':
                    self.np[i] = (g_curr, r_curr, b_curr)
                elif order == 'BRG':
                    self.np[i] = (b_curr, r_curr, g_curr)
                elif order == 'RBG':
                    self.np[i] = (r_curr, b_curr, g_curr)
                else:
                    self.np[i] = (r_curr, g_curr, b_curr)
            self.np.write()

    def clear(self):
        """Apaga todos los LEDs."""
        self.set_color(0, 0, 0)

    def _simulate_print(self, r, g, b):
        """Simula la tira de LEDs en consola CPython."""
        ansi_color = f"\033[38;2;{r};{g};{b}m"
        reset = "\033[0m"
        blocks = "■" * min(15, self.led_count)
        print(f"[LED Simulator] Color cambiado a: {ansi_color}{blocks}{reset} (RGB: {r}, {g}, {b})")

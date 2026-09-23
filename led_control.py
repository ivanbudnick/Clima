import sys
import config
import time
import gc

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

def map_color(r, g, b, order):
    """Mapea la tupla (R, G, B) según el orden físico de los LEDs."""
    if order == 'GRB':
        return (g, r, b)
    if order == 'BRG':
        return (b, r, g)
    if order == 'RBG':
        return (r, b, g)
    return (r, g, b)

class LEDController:
    def __init__(self, pin_num, led_count):
        self.pin_num = pin_num
        self.led_count = led_count
        self.current_color = (0, 0, 0)
        self.current_physical = (0, 0, 0)
        self.mode = "STATIC"
        self.last_tick = 0
        self.step_counter = 0
        self.pixel_states = [0] * led_count
        
        if IS_MICROPYTHON:
            pin = machine.Pin(pin_num, machine.Pin.OUT)
            self.np = neopixel.NeoPixel(pin, led_count)
            self.clear()
        else:
            self.np = None
            print(f"[LED Simulator] Inicializado con {led_count} LEDs.")
            self.clear()

    def set_color(self, r, g, b):
        """Aplica un color estático de forma instantánea."""
        self.current_color = (r, g, b)
        self.mode = "STATIC"
        self.pixel_states = [0] * self.led_count
        
        if IS_MICROPYTHON:
            factor = getattr(config, 'FACTOR_BRILLO', 0.15)
            r_target = int(r * factor)
            g_target = int(g * factor)
            b_target = int(b * factor)
            order = getattr(config, 'COLOR_ORDER', 'RGB')
            pixel = map_color(r_target, g_target, b_target, order)
            for i in range(self.led_count):
                self.np[i] = pixel
            self.np.write()
            self.current_physical = (r_target, g_target, b_target)
        else:
            self._simulate_print(r, g, b)

    def set_mode(self, mode_name, rgb):
        """Configura el modo de animación y realiza una transición suave hacia el nuevo color base."""
        self.mode = mode_name
        self.current_color = rgb
        self.pixel_states = [0] * self.led_count
        self.fade_to(rgb[0], rgb[1], rgb[2])

    def fade_to(self, r, g, b):
        """Transición progresiva en 15 pasos."""
        if IS_MICROPYTHON:
            factor = getattr(config, 'FACTOR_BRILLO', 0.15)
            r_target = int(r * factor)
            g_target = int(g * factor)
            b_target = int(b * factor)
            r_start, g_start, b_start = self.current_physical
            order = getattr(config, 'COLOR_ORDER', 'RGB')
            
            steps = 15
            for step in range(1, steps + 1):
                r_curr = int(r_start + (r_target - r_start) * step / steps)
                g_curr = int(g_start + (g_target - g_start) * step / steps)
                b_curr = int(b_start + (b_target - b_start) * step / steps)
                pixel = map_color(r_curr, g_curr, b_curr, order)
                for i in range(self.led_count):
                    self.np[i] = pixel
                self.np.write()
                time.sleep_ms(10)
                
            self.current_physical = (r_target, g_target, b_target)
        else:
            self._simulate_print(r, g, b)

    def update(self):
        """Actualiza el frame de animación según el modo activo."""
        if not IS_MICROPYTHON or self.mode == "STATIC":
            return
            
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_tick) < 50:
            return
        self.last_tick = now
        
        factor = getattr(config, 'FACTOR_BRILLO', 0.15)
        order = getattr(config, 'COLOR_ORDER', 'RGB')
        
        if self.mode in ("RAIN", "DRIZZLE", "THUNDERSTORM"):
            r_base, g_base, b_base = self.current_color
            r_phys = int(r_base * factor)
            g_phys = int(g_base * factor)
            b_phys = int(b_base * factor)
            
            for i in range(self.led_count):
                state = self.pixel_states[i]
                if state == 0:
                    rand = get_random()
                    if rand < 0.02:
                        self.pixel_states[i] = 3
                        state = 3
                    elif rand < 0.09:
                        self.pixel_states[i] = -5
                        state = -5
                
                if state > 0:
                    mult = 1.0 + (1.5 * state / 3)
                    r_curr = min(255, int(r_phys * mult + (40 * state)))
                    g_curr = min(255, int(g_phys * mult + (20 * state)))
                    b_curr = min(255, int(b_phys * mult + (40 * state)))
                    self.pixel_states[i] -= 1
                elif state < 0:
                    mult = 0.1 + 0.9 * (5 + state) / 5.0
                    r_curr = int(r_phys * mult)
                    g_curr = int(g_phys * mult)
                    b_curr = int(b_phys * mult)
                    self.pixel_states[i] += 1
                else:
                    r_curr, g_curr, b_curr = r_phys, g_phys, b_phys
                
                self.np[i] = map_color(r_curr, g_curr, b_curr, order)
            self.np.write()
            
        elif self.mode == "CLEAR_DAY":
            self.step_counter = (self.step_counter + 1) % 80
            if self.step_counter < 40:
                breath = 0.45 + (0.55 * self.step_counter / 40)
            else:
                breath = 0.45 + (0.55 * (80 - self.step_counter) / 40)
                
            pixel_factor = factor * breath
            gradient_colors = [
                (255, 110, 0), (255, 160, 0), (255, 205, 0),
                (255, 225, 0), (255, 175, 0), (255, 120, 0)
            ]
            
            for i in range(self.led_count):
                r_base, g_base, b_base = gradient_colors[i % len(gradient_colors)]
                r_curr = int(r_base * pixel_factor)
                g_curr = int(g_base * pixel_factor)
                b_curr = int(b_base * pixel_factor)
                self.np[i] = map_color(r_curr, g_curr, b_curr, order)
            self.np.write()
            
        elif self.mode == "CLEAR_NIGHT":
            r_base, g_base, b_base = self.current_color
            r_phys = int(r_base * factor)
            g_phys = int(g_base * factor)
            b_phys = int(b_base * factor)
            
            for i in range(self.led_count):
                state = self.pixel_states[i]
                if state == 0:
                    rand = get_random()
                    if rand < 0.015:
                        self.pixel_states[i] = 10
                        state = 10
                
                if state > 0:
                    mult = 1.0 + 0.6 * (state - 5) / 5.0
                    r_curr = max(0, min(255, int(r_phys * mult)))
                    g_curr = max(0, min(255, int(g_phys * mult)))
                    b_curr = max(0, min(255, int(b_phys * mult)))
                    self.pixel_states[i] -= 1
                else:
                    r_curr, g_curr, b_curr = r_phys, g_phys, b_phys
                    
                self.np[i] = map_color(r_curr, g_curr, b_curr, order)
            self.np.write()
            
        else:
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
                self.np[i] = map_color(r_curr, g_curr, b_curr, order)
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

import sys

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
        
        if IS_MICROPYTHON:
            # On MicroPython, initialize the physical NeoPixel strip
            # Pin is configured as output
            pin = machine.Pin(pin_num, machine.Pin.OUT)
            self.np = neopixel.NeoPixel(pin, led_count)
            self.clear()
        else:
            self.np = None
            print(f"[LED Simulator] Inicializado con {led_count} LEDs (Simulado en Pin GPIO {pin_num}).")
            self.clear()

    def set_color(self, r, g, b):
        """
        Sets all LEDs on the strip to the specified RGB color.
        """
        self.current_color = (r, g, b)
        
        if IS_MICROPYTHON:
            for i in range(self.led_count):
                self.np[i] = (r, g, b)
            self.np.write()
        else:
            # Simulate the LED strip in the terminal using TrueColor ANSI sequences
            # \033[38;2;r;g;bm sets the foreground text color to RGB (r, g, b)
            ansi_color = f"\033[38;2;{r};{g};{b}m"
            reset = "\033[0m"
            blocks = "■" * min(15, self.led_count)  # Print up to 15 blocks to represent the strip
            print(f"[LED Simulator] Color cambiado a: {ansi_color}{blocks}{reset} (RGB: {r}, {g}, {b})")

    def clear(self):
        """
        Turns off all LEDs.
        """
        self.set_color(0, 0, 0)

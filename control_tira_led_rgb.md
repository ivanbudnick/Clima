# 💡 Guía de Proyecto: Control de Tira LED RGB Direccionable (WS2811 12V) - Versión Simplificada

Este documento detalla la planificación, componentes y el conexionado necesario para configurar una tira LED RGB direccionable simplificando el hardware al prescindir de potenciómetros y pulsadores físicos. El control de encendido, apagado, color e intensidad se gestiona directamente desde el microcontrolador mediante código a medida (programación) y el control físico de encendido general se reduce a un interruptor clásico insertado en el cable de alimentación.

---

## 📋 Lista de Componentes

### De tu Inventario

* **Microcontrolador**: `Módulo ESP32 / ESP8266 (NodeMCU / DevKit)` (Modelo específico seleccionado: **NodeMCU ESP8266 4MB ESP-12E WiFi PWM I2C** [Foto de origen: IMG_5031.jpeg](file:///Users/ivanbudnick/Documents/Inventario/IMG_5031.jpeg)). Encargado del control lógico y la conectividad inalámbrica del proyecto.
* **Tira LED**: `Tira de LED RGB Digital` (2.5 metros con 75 LEDs, protocolo WS2811). Cuenta con sus 3 cables pre-soldados en el extremo.
* **Fuente de Alimentación**: `Fuente de alimentación / Adaptador AC/DC (Sagemcom)` (Salida: 12V 2.0A). Soporta perfectamente la corriente requerida por la tira.
* **Conector de Corriente**: `Conector Jack DC hembra para chasis (DC-022)` (para recibir la ficha de la fuente de 12V sin cortarla).
* **Módulo Regulador Step-Down (Buck Converter)**: `Módulo Regulador Step-Down DC-DC LM2596 (HW-411)`. Reduce los 12V de la fuente principal a 5V para alimentar el microcontrolador por su pin `VIN` / `5V`.
* **Condensador Electrolítico**: `Capacitor Electrolítico 2200 µF / 16V`. Se conecta en paralelo a las líneas de alimentación de la tira LED para absorber picos de corriente. *(Nota: El voltaje de 16V tiene menor margen de seguridad sobre los 12V de alimentación que un capacitor de 25V, por lo que es crítico respetar estrictamente la polaridad en la conexión).*
* **Componentes Pasivos**:
  * `Resistencia de 470 Ω` o `220 Ω` (de tu pack de resistencias surtidas, para la línea de datos DIN).
* **Montaje y Pruebas**:
  * `Protoboard MB-102` y `Cables Jumper DuPont` (macho-macho / macho-hembra).
  * `Cables unipolares de 0.25mm` para el armado definitivo.
  * `Soldador tipo lápiz` Zurich, `Estaño` y `Tubo termocontraíble` para aislar las uniones soldadas.
  * `Interruptor de paso clásico` (Interruptor de velador, de color negro).
  * **Herramientas**: `Multímetro Digital Uni-T UT33A+` (auto-rango con medición de capacitancia, continuidad y corrientes de hasta 10A).

### Sugeridos para Adquirir

1. **Conversor de Nivel Lógico (Level Shifter 3.3V a 5V)** (ej. `74HCT125` o `74AHCT125` en formato DIP-14):
   * *Justificación*: Eleva la señal de datos de 3.3V del microcontrolador a los 5V que requiere el chip WS2811 de la tira LED, previniendo parpadeos y ruidos en la señal a alta velocidad (800 kHz).
   * *Nota*: Es muy importante que sea la variante con la letra **T** intermedia (**HCT** o **AHCT**) para que detecte correctamente los 3.3V del microcontrolador como nivel lógico alto estando alimentado a 5V. Aunque es factible implementar de forma temporal el "truco del diodo 1N4007" o un circuito con transistores NPN 2N2222 y resistencias de tu inventario, adquirir el integrado dedicado asegura la estabilidad definitiva de la señal.

---

## 🔌 Esquema del Conexionado

### Identificación de los 3 cables de la Tira LED:
* **Cable Rojo**: Entrada de Alimentación Positiva (`+12V`).
* **Cable Negro** (o Blanco): Masa/Retorno (`GND`).
* **Cable Central** (Verde o Amarillo): Línea de datos direccionable (`DIN` / `Data`).

### Esquema de Conexiones:

1. **Preparación de Alimentación e Interruptor**:
   * **Opción con interruptor en 12V**: 
     * Soldar un cable al pin negativo (`GND`) del **Jack DC Hembra (DC-022)** y llevarlo a la **línea azul/negra (GND)** de la protoboard.
     * Soldar un cable al pin positivo (`+12V`) del Jack DC, conectarlo a un extremo del **interruptor de paso**, y desde el otro extremo del interruptor llevar un cable hacia la **línea roja (+12V)** de la protoboard.
   * **Opción con interruptor en 220V (Recomendada)**:
     * Instalar el interruptor de velador interrumpiendo una de las fases del cable de red (220V) antes de la fuente de alimentación.
     * Soldar directamente los terminales positivo y negativo del Jack DC Hembra a las líneas de alimentación (`+12V` y `GND`) de la protoboard.

2. **Conexión de la Tira LED**:
   * Conectar el **cable positivo (+12V)** de la tira (Rojo) a la **línea de +12V** de la protoboard.
   * Conectar el **cable de masa (GND)** de la tira (Negro) a la **línea de GND** de la protoboard.
   * Conectar el **cable de datos central (DIN)** de la tira (Verde/Amarillo) a una columna vacía y aislada de la protoboard.

3. **Conexión del Microcontrolador (NodeMCU ESP8266)**:
   * Insertar el NodeMCU ESP8266 en la protoboard.
   * Conectar un pin **GND** del microcontrolador a la **línea de GND** de la protoboard (para unificar masas comunes).
   * *Alimentación*: Inicialmente alimentarlo por USB. Para el armado definitivo, conectar la salida regulada de 5V del Step-Down al pin **VIN** (o **5V**) y el pin **GND** del NodeMCU.

4. **Línea de Datos (DIN)**:
   * Colocar una **resistencia de 470 Ω** (o 220 Ω) en la protoboard:
     * Un extremo va conectado al pin digital de salida del NodeMCU ESP8266 (ej. pin **D4**, que corresponde internamente a `GPIO 2`).
     * El otro extremo va conectado a la columna de la protoboard donde se insertó el **cable de datos (DIN)** de la tira LED.

---

## 🛠️ Control y Programación mediante Código

Al prescindir de controles físicos como potenciómetros o pulsadores, toda la lógica de encendido, apagado, regulación de brillo y selección de colores se realiza directamente en el código del microcontrolador.

Para esto, se recomienda utilizar la biblioteca **FastLED** (una de las más eficientes y populares para el control de LEDs direccionables en Arduino/ESP32).

### Código de Ejemplo (Arduino / ESP32)

El siguiente ejemplo demuestra cómo estructurar funciones en tu código para controlar:
1. **Encendido y Apagado (On/Off)** de forma lógica.
2. **Brillo (Intensidad)**.
3. **Color** de la tira completa.

```cpp
#include <FastLED.h>

#define NUM_LEDS 75
#define DATA_PIN 2 // GPIO 2 en ESP32 o D4 en ESP8266

CRGB leds[NUM_LEDS];

// Variables de estado de la tira
bool tiraEncendida = true;
uint8_t brilloActual = 128; // Rango de 0 (apagado) a 255 (brillo máximo)
CRGB colorActual = CRGB(255, 147, 41); // Color inicial (Blanco Cálido)

// Declaración de funciones de control
void actualizarTira();
void encenderTira();
void apagarTira();
void establecerBrillo(uint8_t nuevoBrillo);
void establecerColor(CRGB nuevoColor);

void setup() {
  // Inicialización de la tira LED (protocolo WS2811, orden de color GRB)
  FastLED.addLeds<WS2811, DATA_PIN, GRB>(leds, NUM_LEDS);
  
  // Aplicamos el estado inicial
  actualizarTira();
}

void loop() {
  // Aquí puedes programar tu lógica temporal, temporizadores, 
  // secuencias de efectos, o integrar comunicación (Serial, Bluetooth, etc.)
  
  // Ejemplo de simulación:
  // 1. Después de un tiempo, cambiar el color a Azul
  delay(5000);
  establecerColor(CRGB(0, 0, 255));
  
  // 2. Bajar la intensidad (brillo) a la mitad
  delay(5000);
  establecerBrillo(64);
  
  // 3. Apagar la tira
  delay(5000);
  apagarTira();
  
  // 4. Volver a encender en Blanco Cálido y brillo original
  delay(5000);
  establecerColor(CRGB(255, 147, 41));
  establecerBrillo(128);
  encenderTira();
}

// --- Funciones de Control ---

// Aplica el color y el brillo en base al estado de encendido
void actualizarTira() {
  if (tiraEncendida) {
    FastLED.setBrightness(brilloActual);
    fill_solid(leds, NUM_LEDS, colorActual);
  } else {
    // Si está apagada lógicamente, ponemos el brillo en 0 y limpiamos los leds
    FastLED.setBrightness(0);
    fill_solid(leds, NUM_LEDS, CRGB::Black);
  }
  FastLED.show();
}

// Enciende la tira (restaurando el último color y brillo configurados)
void encenderTira() {
  tiraEncendida = true;
  actualizarTira();
}

// Apaga la tira de forma lógica (sin cortar la alimentación del ESP32)
void apagarTira() {
  tiraEncendida = false;
  actualizarTira();
}

// Cambia el brillo de la tira
void establecerBrillo(uint8_t nuevoBrillo) {
  brilloActual = nuevoBrillo;
  actualizarTira();
}

// Cambia el color de la tira
void establecerColor(CRGB nuevoColor) {
  colorActual = nuevoColor;
  actualizarTira();
}
```

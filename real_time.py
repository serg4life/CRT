import time
import os
import ctypes
import RPi.GPIO as GPIO
from multiprocessing import Process, Queue
import board
import digitalio
import adafruit_ssd1306

# Configuración de GPIO
GPIO.setmode(GPIO.BCM)
fotodiodo_incrementar = 17  # Pin para el fotodiodo que incrementa
fotodiodo_decrementar = 27  # Pin para el fotodiodo que decrementa
boton_reset = 22            # Pin para el botón de reset
led_rojo = 18               # Pin para el LED rojo

# Configura los pines como entrada/salida con resistencias pull-down
GPIO.setup(fotodiodo_incrementar, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(fotodiodo_decrementar, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(boton_reset, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(led_rojo, GPIO.OUT)

# Cola para compartir datos entre tareas
cola_contador = Queue()

# Constantes para tiempo real
NSEC_PER_SEC = 1000000000
CLOCK_REALTIME = 0
TIMER_ABSTIME = 1

# Estructura para tiempos
class timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

# Cargar librería de tiempo real
librt = ctypes.CDLL('librt.so.6', mode=ctypes.RTLD_GLOBAL)

# Normalizar tiempos
def tsnorm(ts):
    while ts.tv_nsec >= NSEC_PER_SEC:
        ts.tv_nsec -= NSEC_PER_SEC
        ts.tv_sec += 1

# Tarea de tiempo real para los fotodiodos
def tarea_fotodiodos(cola):
    contador = 0
    while True:
        # Leer el estado de los fotodiodos
        if GPIO.input(fotodiodo_incrementar) == GPIO.HIGH:
            contador += 1
            print("Contador incrementado:", contador)
            cola.put(contador)  # Enviar el valor a la cola
            time.sleep(0.1)  # Debounce

        if GPIO.input(fotodiodo_decrementar) == GPIO.HIGH:
            contador -= 1
            print("Contador decrementado:", contador)
            cola.put(contador)  # Enviar el valor a la cola
            time.sleep(0.1)  # Debounce

# Tarea de tiempo real de mayor prioridad para el botón
def tarea_boton():
    while True:
        if GPIO.input(boton_reset) == GPIO.HIGH:
            GPIO.output(led_rojo, GPIO.HIGH)  # Encender LED rojo
            print("Botón presionado: LED rojo encendido")
            time.sleep(1)  # Mantener el LED encendido por 1 segundo
            GPIO.output(led_rojo, GPIO.LOW)  # Apagar LED rojo
            time.sleep(0.1)  # Debounce

# Tarea no crítica para la pantalla OLED
def tarea_oled(cola):
    # Configuración de la pantalla OLED
    i2c = board.I2C()
    oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

    while True:
        if not cola.empty():
            contador = cola.get()
            oled.fill(0)  # Limpiar pantalla
            oled.text(f"Contador: {contador}", 0, 0, 1)
            oled.show()  # Mostrar el valor en la pantalla

# Configurar prioridad de tiempo real
def configurar_tiempo_real(prio):
    param = os.sched_param(prio)
    print(f"Configurando prioridad de tiempo real: {prio}")
    try:
        os.sched_setscheduler(0, os.SCHED_FIFO, param)
    except PermissionError:
        print("Error: Se requieren privilegios de superusuario para establecer prioridad de tiempo real.")
        os._exit(-1)

# Función principal
if __name__ == "__main__":
    # Configurar prioridades de tiempo real
    configurar_tiempo_real(20)  # Prioridad para fotodiodos
    configurar_tiempo_real(30)  # Prioridad más alta para el botón

    # Crear procesos para las tareas
    proceso_fotodiodos = Process(target=tarea_fotodiodos, args=(cola_contador,))
    proceso_boton = Process(target=tarea_boton)
    proceso_oled = Process(target=tarea_oled, args=(cola_contador,))

    # Iniciar procesos
    proceso_fotodiodos.start()
    proceso_boton.start()
    proceso_oled.start()

    # Esperar a que los procesos terminen (no deberían)
    proceso_fotodiodos.join()
    proceso_boton.join()
    proceso_oled.join()
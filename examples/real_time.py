import time
import os
import ctypes
import RPi.GPIO as GPIO
from multiprocessing import Process, Queue
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from time import sleep

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
    # Inicializa la comunicación I²C y el dispositivo OLED
    serial = i2c(port=1, address=0x3C)  # El address puede ser 0x3C o 0x3D, depende del display
    device = ssd1306(serial)

    while True:
        if not cola.empty():
            contador = cola.get()
            # Limpia la pantalla
            device.clear()

            # Dibuja el valor del contador en la pantalla
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((10, 20), f"Contador: {contador}", fill="white")

# Configurar prioridad de tiempo real
def set_priority(pid: int, prio: int):
    param = os.sched_param(prio)
    print(f"Configurando prioridad de tiempo real: {prio}")
    try:
        os.sched_setscheduler(pid, os.SCHED_FIFO, param)
    except PermissionError:
        print("Error: Se requieren privilegios de superusuario para establecer prioridad de tiempo real.")
        os._exit(-1)

# Función principal
if __name__ == "__main__":
    # Crear procesos para las tareas
    proceso_fotodiodos = Process(target=tarea_fotodiodos, args=(cola_contador,))
    proceso_boton = Process(target=tarea_boton)
    proceso_oled = Process(target=tarea_oled, args=(cola_contador,))

    # Iniciar procesos
    proceso_fotodiodos.start()
    proceso_boton.start()
    proceso_oled.start()

    # Configurar prioridades de tiempo real después de iniciar los procesos
    set_priority(proceso_fotodiodos.pid, 20)
    set_priority(proceso_boton.pid, 30)
    # Esperar a que los procesos terminen (no deberían)
    proceso_fotodiodos.join()
    proceso_boton.join()
    proceso_oled.join()
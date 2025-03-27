#!/bin/python

from gpiozero import Button, LED
from gpiozero import Device
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from multiprocessing import Process, Queue, Value
import ctypes
import time

from ctypes import c_bool
from tasks import tarea_oled, set_priority, button_callback, increment_callback, decrement_callback

# Configuración de GPIO
fotodiodo_incrementar = Button(17, pull_up=False)
fotodiodo_decrementar = Button(27, pull_up=False)
boton_reset = Button(22, pull_up=False)
led_rojo = LED(5)

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
librt = ctypes.CDLL('libc.so.6', mode=ctypes.RTLD_GLOBAL)

# Normalizar tiempos
def tsnorm(ts):
    while ts.tv_nsec >= NSEC_PER_SEC:
        ts.tv_nsec -= NSEC_PER_SEC
        ts.tv_sec += 1

# Función principal
if __name__ == "__main__":
    running = Value(c_bool, True)
    
    while True:
            try:
                serial = i2c(port=1, address=0x3C)
                device = ssd1306(serial)
                print("¡Pantalla OLED inicializada correctamente!")
                break
            except Exception as e:
                print(f"Error al inicializar la pantalla OLED: {e}")
                time.sleep(0.5)
    
    # Configurar interrupciones
    fotodiodo_incrementar.when_activated = lambda: increment_callback(cola_contador, running)
    fotodiodo_decrementar.when_activated = lambda: decrement_callback(cola_contador, running)
    boton_reset.when_activated = lambda: button_callback(led_rojo, running, device)

    # Crear procesos para las tareas
    proceso_oled = Process(target=tarea_oled, args=(cola_contador, running, device))

    try:
        # Iniciar procesos
        proceso_oled.start()
        set_priority(0, 90)
        set_priority(proceso_oled.pid, 20)
        proceso_oled.join()
        
    except PermissionError:
        print("❌ Error: Se requieren permisos de superusuario para ejecutar esta acción.")
        print("🔹 Prueba ejecutando con: sudo")
        
    except KeyboardInterrupt:
        print("Interrupción detectada, deteniendo todas las tareas...")
        running.value = False
        proceso_oled.join()
        Device.close()

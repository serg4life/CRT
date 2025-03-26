import RPi.GPIO as GPIO
from multiprocessing import Process, Queue
import ctypes

from tasks import diode_task, tarea_boton, tarea_oled, set_priority

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
librt = ctypes.CDLL('libc.so.6', mode=ctypes.RTLD_GLOBAL)

# Normalizar tiempos
def tsnorm(ts):
    while ts.tv_nsec >= NSEC_PER_SEC:
        ts.tv_nsec -= NSEC_PER_SEC
        ts.tv_sec += 1

# Función principal
if __name__ == "__main__":
    # Crear procesos para las tareas
    proceso_fotodiodos = Process(target=diode_task, args=(cola_contador, fotodiodo_incrementar, fotodiodo_decrementar))
    proceso_boton = Process(target=tarea_boton, args=(boton_reset, led_rojo))
    proceso_oled = Process(target=tarea_oled, args=(cola_contador,))  # Usando valores predeterminados para i2c_port e i2c_address


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
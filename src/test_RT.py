#!/bin/python

import RPi.GPIO as GPIO
from multiprocessing import Process, Queue, Value
import ctypes
from ctypes import c_bool
from tasks import diode_task, tarea_boton, tarea_oled, set_priority, button_callback, increment_callback, decrement_callback

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
    running = Value(c_bool, True)
    
    # Configurar interrupciones
    GPIO.add_event_detect(fotodiodo_incrementar, GPIO.RISING, callback=lambda channel: increment_callback(channel, cola_contador, running), bouncetime=100)
    GPIO.add_event_detect(fotodiodo_decrementar, GPIO.RISING, callback=lambda channel: decrement_callback(channel, cola_contador, running), bouncetime=100)
    GPIO.add_event_detect(boton_reset, GPIO.RISING, callback=lambda channel: button_callback(channel, led_rojo, running), bouncetime=100)

    # Crear procesos para las tareas
    #proceso_fotodiodos = Process(target=diode_task, args=(cola_contador, fotodiodo_incrementar, fotodiodo_decrementar, running))
    #proceso_boton = Process(target=tarea_boton, args=(boton_reset, led_rojo, running))
    proceso_oled = Process(target=tarea_oled, args=(cola_contador,running))  # Usando valores predeterminados para i2c_port e i2c_address

    try:
        # Iniciar procesos
        #proceso_fotodiodos.start()
        #proceso_boton.start()
        proceso_oled.start()
        set_priority(0, 90)
        # Configurar prioridades de tiempo real después de iniciar los procesos
        #set_priority(proceso_fotodiodos.pid, 20)
        #set_priority(proceso_boton.pid, 30)
        set_priority(proceso_oled.pid, 10)
        # Esperar a que los procesos terminen (no deberían)
        #proceso_fotodiodos.join()
        #proceso_boton.join()
        proceso_oled.join()
    except KeyboardInterrupt:
        print("Interrupción detectada, deteniendo todas las tareas...")
        running.value = False
        proceso_oled.join()
        GPIO.cleanup()
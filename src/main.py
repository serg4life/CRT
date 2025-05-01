#!/bin/python

from gpiozero import Button, LED
from gpiozero import Device
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from multiprocessing import Process, Value
import ctypes
import time

from shared_resources import contador_queue
from ctypes import c_bool
from tasks import tarea_oled, set_priority, button_callback, increment_callback, decrement_callback
from ContadorLocal import ContadorLocal

# Configuración de GPIO
fotodiodo_incrementar = Button(17, pull_up=True)
fotodiodo_decrementar = Button(27, pull_up=True)
boton_reset = Button(22, pull_up=True)
led_rojo = LED(5)

# vInstancia del objeto ContadorLocal
contador_local = ContadorLocal(contador_queue)
        
# Función principal
if __name__ == "__main__":
    running = Value(c_bool, True)
    emergency = Value(c_bool, False)
    
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
    fotodiodo_incrementar.when_deactivated = lambda: increment_callback(contador_local, running)
    fotodiodo_decrementar.when_deactivated = lambda: decrement_callback(contador_local, running)
    boton_reset.when_deactivated = lambda: button_callback(led_rojo, running, emergency)

    # Crear procesos para las tareas
    proceso_oled = Process(target=tarea_oled, args=(running, device))

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

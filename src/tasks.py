import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
import time
import os
from multiprocessing import Queue, Value
from ctypes import c_bool

# Callback para el fotodiodo que incrementa (REVISAR CALLBACKS)
def increment_callback(channel, cola, running):
    if running.value:
        contador = cola.get() if not cola.empty() else 0
        contador += 1
        print("Contador incrementado:", contador)
        cola.put(contador)

# Callback para el fotodiodo que decrementa
def decrement_callback(channel, cola, running):
    if running.value:
        contador = cola.get() if not cola.empty() else 0
        contador -= 1
        print("Contador decrementado:", contador)
        cola.put(contador)

# Callback para el botón
def button_callback(channel, led_pin, running):
    if running.value:
        GPIO.output(led_pin, GPIO.HIGH)  # Encender LED rojo
        print("Botón presionado: LED rojo encendido")
        time.sleep(1)  # Mantener el LED encendido por 1 segundo
        GPIO.output(led_pin, GPIO.LOW)  # Apagar LED rojo

# Tarea de tiempo real para los fotodiodos
def diode_task(cola: Queue, increment_diode_pin: int, decrement_diode_pin: int, running: 'Value'):
    contador = 0
    try:
        while running.value:
            # Leer el estado de los fotodiodos
            if GPIO.input(increment_diode_pin) == GPIO.HIGH:
                contador += 1
                print("Contador incrementado:", contador)
                cola.put(contador)  # Enviar el valor a la cola
                time.sleep(0.1)  # Debounce

            if GPIO.input(decrement_diode_pin) == GPIO.HIGH:
                contador -= 1
                print("Contador decrementado:", contador)
                cola.put(contador)  # Enviar el valor a la cola
                time.sleep(0.1)  # Debounce
    except KeyboardInterrupt:
        print("diode_task interrupted by the user")
        
# Tarea de tiempo real de mayor prioridad para el botón
def tarea_boton(button_pin: int, led_pin: int, running: 'Value'):
    try:
        while running.value:
            if GPIO.input(button_pin) == GPIO.HIGH:
                GPIO.output(led_pin, GPIO.HIGH)  # Encender LED rojo
                print("Botón presionado: LED rojo encendido")
                time.sleep(1)  # Mantener el LED encendido por 1 segundo
                GPIO.output(led_pin, GPIO.LOW)  # Apagar LED rojo
                time.sleep(0.1)  # Debounce
    except KeyboardInterrupt:
        print("tarea_boton interrupted by the user")

# Tarea no crítica para la pantalla OLED
def tarea_oled(cola: Queue, running: 'Value', i2c_port: int = 1, i2c_address: int = 0x3C):
    try:
        # Inicializa la comunicación I²C y el dispositivo OLED
        while running.value:
            try:
                serial = i2c(i2c_port, i2c_address)  # El address puede ser 0x3C o 0x3D, depende del display
                device = ssd1306(serial)
                print("¡Pantalla OLED inicializada!")
                break
            except:
                time.sleep(0.5)
                print("Error al inicializar la pantalla OLED. Reintentando...")
                
        while running.value:
            if not cola.empty():
                contador = cola.get()
                # Limpia la pantalla
                device.clear()

                # Dibuja el valor del contador en la pantalla
                with canvas(device) as draw:
                    draw.rectangle(device.bounding_box, outline="white", fill="black")
                    draw.text((10, 20), f"Contador: {contador}", fill="white")
    except KeyboardInterrupt:
        print("tarea_oled interrupted by the user")

# Configurar prioridad de tiempo real
def set_priority(pid: int, prio: int):
    param = os.sched_param(prio)
    print(f"Configurando prioridad de tiempo real: {prio}")
    try:
        os.sched_setscheduler(pid, os.SCHED_FIFO, param)
    except PermissionError:
        print("Error: Se requieren privilegios de superusuario para establecer prioridad de tiempo real.")
        os._exit(-1)
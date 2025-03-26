import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
import time
import os
from multiprocessing import Queue

# Tarea de tiempo real para los fotodiodos
def diode_task(cola: Queue, increment_diode_pin: int, decrement_diode_pin: int):
    contador = 0
    while True:
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

# Tarea de tiempo real de mayor prioridad para el botón
def tarea_boton(button_pin: int, led_pin: int):
    while True:
        if GPIO.input(button_pin) == GPIO.HIGH:
            GPIO.output(led_pin, GPIO.HIGH)  # Encender LED rojo
            print("Botón presionado: LED rojo encendido")
            time.sleep(1)  # Mantener el LED encendido por 1 segundo
            GPIO.output(led_pin, GPIO.LOW)  # Apagar LED rojo
            time.sleep(0.1)  # Debounce

# Tarea no crítica para la pantalla OLED
def tarea_oled(cola: Queue, i2c_port: int = 1, i2c_address: int = 0x3C):
    # Inicializa la comunicación I²C y el dispositivo OLED
    serial = i2c(i2c_port, i2c_address)  # El address puede ser 0x3C o 0x3D, depende del display
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
from gpiozero import Button, LED
from gpiozero import Device
from luma.core.render import canvas
from luma.oled.device import ssd1306
import time
import os
from multiprocessing import Queue, Value

# Callback para el fotodiodo que incrementa
def increment_callback(cola, running: 'Value'):
    if running.value:
        contador = cola.get() if not cola.empty() else 0
        contador += 1
        #print("Contador incrementado:", contador)
        cola.put(contador)

# Callback para el fotodiodo que decrementa
def decrement_callback(cola, running):
    if running.value:
        contador = cola.get() if not cola.empty() else 0
        contador -= 1
        #print("Contador decrementado:", contador)
        cola.put(contador)

# Callback para el botón
def button_callback(led, running: 'Value', device: ssd1306):
    if running.value:
        led.on()
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 20), "ALERTA!", fill="white")
            draw.text((10, 40), "Botón presionado", fill="white")
        #print("Botón presionado: LED rojo encendido")
        time.sleep(3)
        #device.clear() (ESTO HACERLO EN LA TAREA OLED? INDICANDOSELO CON ALGUN FLAG?)
        #with canvas(device) as draw:
            #draw.rectangle(device.bounding_box, outline="white", fill="black")
        led.off()

# Tarea de tiempo real para los fotodiodos
def diode_task(cola: Queue, increment_diode: Button, decrement_diode: Button, running: 'Value'):
    contador = 0
    try:
        while running.value:
            if increment_diode.is_pressed:
                contador += 1
                #print("Contador incrementado:", contador)
                cola.put(contador)
                time.sleep(0.1)
            if decrement_diode.is_pressed:
                contador -= 1
                #print("Contador decrementado:", contador)
                cola.put(contador)
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("diode_task interrupted by the user")
        Device.close()

# Tarea de tiempo real de mayor prioridad para el botón
def tarea_boton(button: Button, led: LED, running: 'Value'):
    try:
        while running.value:
            if button.is_active:
                led.on()
                #print("Botón presionado: LED rojo encendido")
                time.sleep(1)
                led.off()
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("tarea_boton interrupted by the user")
        Device.close()

# Tarea no crítica para la pantalla OLED
def tarea_oled(cola: Queue, running: 'Value', device: ssd1306):
    # CONFIGURAR CON TIMER?
    try:
        device.clear()
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
        while running.value:
            if not cola.empty():
                contador = cola.get()
                device.clear()
                with canvas(device) as draw:
                    draw.rectangle(device.bounding_box, outline="white", fill="black")
                    draw.text((10, 20), f"Contador: {contador}", fill="white")
            time.
    except KeyboardInterrupt:
        print("tarea_oled interrupted by the user")
        Device.close()

# Configurar prioridad de tiempo real
def set_priority(pid: int, prio: int):
    param = os.sched_param(prio)
    print(f"Configurando prioridad de tiempo real: {prio}")
    try:
        os.sched_setscheduler(pid, os.SCHED_FIFO, param)
    except PermissionError:
        print("Error: Se requieren privilegios de superusuario para establecer prioridad de tiempo real.")
        Device.close()
        os._exit(-1)

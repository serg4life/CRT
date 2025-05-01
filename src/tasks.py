from gpiozero import LED
from gpiozero import Device
from luma.core.render import canvas
from luma.oled.device import ssd1306
import time
import os
from multiprocessing import Queue, Value, Process

from shared_resources import contador_queue
from ContadorLocal import ContadorLocal

# Variables para debounce, para evitar multiples detecciones de pulsos.
DEBOUNCE_TIME = 0.2
last_interrupt_time_increment = 0
last_interrupt_time_decrement = 0

# Callback para el fotodiodo que incrementa
def increment_callback(contador: ContadorLocal, running: 'Value'):
    global last_interrupt_time_increment
    current_time = time.time()
    if current_time - last_interrupt_time_increment > DEBOUNCE_TIME:
        last_interrupt_time_increment = current_time
        if running.value:
            contador.incrementar() # Dentro de esta funcion se gestiona el lock y la cola.

# Callback para el fotodiodo que decrementa
def decrement_callback(contador: ContadorLocal, running: 'Value'):
    global last_interrupt_time_decrement
    current_time = time.time()
    if current_time - last_interrupt_time_decrement > DEBOUNCE_TIME:
        last_interrupt_time_decrement = current_time
        if running.value:
            contador.decrementar() # Dentro de esta funcion se gestiona el lock y la cola.

def blink_led(led, emergency: 'Value'):
        led.on()
        time.sleep(1)
        led.off()
        emergency.value = False # Para que solo se pueda establecer una emergencia a la vez.

# Callback para el botón
def button_callback(led, running: 'Value', emergency: 'Value'):
    if running.value:
        if not emergency.value:
            emergency.value = True
            p = Process(target=blink_led, args=(led, emergency))
            p.start()
            set_priority(p.pid, 90)
            

# Tarea no crítica para la pantalla OLED
def tarea_oled(running: 'Value', device: ssd1306):
    # CONFIGURAR CON TIMER?
    try:
        device.clear()
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
        while running.value:
            if not contador_queue.empty():
                value = contador_queue.get()
                device.clear()
                with canvas(device) as draw:
                    draw.rectangle(device.bounding_box, outline="white", fill="black")
                    draw.text((10, 20), f"Contador: {value}", fill="white")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("tarea_oled interrupted by the user")
        Device.close()

# Configurar prioridad de tiempo real
def set_priority(pid: int, prio: int):
    param = os.sched_param(prio)
    #print(f"Configurando prioridad de tiempo real: {prio}")
    try:
        os.sched_setscheduler(pid, os.SCHED_FIFO, param)
    except PermissionError:
        print("Error: Se requieren privilegios de superusuario para establecer prioridad de tiempo real.")
        Device.close()
        os._exit(-1)

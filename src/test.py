import os
import time
from multiprocessing import Process, Pipe, Queue, Value
from gpiozero import Button, LED
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from luma.core.render import canvas
import signal

# Configuración de prioridades
RT_PRIORITY_EMERGENCY = 99
RT_PRIORITY_DISPLAY = 50
RT_PRIORITY_NORMAL = 1

# Configuración de pines
EMERGENCY_BTN_PIN = 22
DIODE_INC_PIN = 17
DIODE_DEC_PIN = 27
LED_ROJO = 5

# Constantes para mensajes
MSG_EMERGENCY = 1
MSG_DIODE_INC = 2
MSG_DIODE_DEC = 3
MSG_DISPLAY = 4

def set_realtime_priority(priority):
    """Configura prioridad SCHED_FIFO"""
    param = os.sched_param(priority)
    os.sched_setscheduler(0, os.SCHED_FIFO, param)

class DisplayManager:
    def __init__(self, conn, counter):
        self.conn = conn
        self.counter = counter
        self.serial = i2c(port=1, address=0x3C)
        self.device = ssd1306(self.serial)
        self.clear_display()
    
    def clear_display(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
    
    def update_display(self, msg_type, data):
        with canvas(self.device) as draw:
            # Mostrar contador (valor compartido)
            draw.text((0, 0), f"Contador: {self.counter.value}", fill="white")
            
            if msg_type == MSG_EMERGENCY:
                draw.text((0, 10), "!EMERGENCIA!", fill="white")
                draw.text((0, 20), data, fill="white")
            elif msg_type == MSG_DIODE_INC:
                draw.text((0, 10), "Incrementado", fill="white")
            elif msg_type == MSG_DIODE_DEC:
                draw.text((0, 10), "Decrementado", fill="white")
            elif msg_type == MSG_DISPLAY:
                draw.text((0, 30), data, fill="white")
    
    def run(self):
        set_realtime_priority(RT_PRIORITY_DISPLAY)
        while True:
            if self.conn.poll(0.01):
                msg_type, data = self.conn.recv()
                self.update_display(msg_type, data)
            else:
                # Actualización periódica
                self.update_display(MSG_DISPLAY, "")

class InterruptManager:
    def __init__(self, conn, counter, led_emergency):
        self.conn = conn
        self.counter = counter
        self.led_emergency = led_emergency
        self.emergency_btn = Button(EMERGENCY_BTN_PIN, pull_up=False, hold_time=0.1)
        self.diode_inc = Button(DIODE_INC_PIN, pull_up=False)
        self.diode_dec = Button(DIODE_DEC_PIN, pull_up=False)
    
    def setup_callbacks(self):
        # Configurar callbacks
        self.emergency_btn.when_activated = self.emergency_callback
        self.emergency_btn.when_deactivated = self.emergency_released
        self.diode_inc.when_activated = self.increment_counter
        self.diode_dec.when_activated = self.decrement_counter
    
    def emergency_callback(self):
        self.led_emergency.on()
        self.conn.send((MSG_EMERGENCY, "Sistema detenido"))
    
    def emergency_released(self):
        self.led_emergency.off()
    
    def increment_counter(self):
        with self.counter.get_lock():
            self.counter.value += 1
        self.conn.send((MSG_DIODE_INC, ""))
    
    def decrement_counter(self):
        with self.counter.get_lock():
            if self.counter.value > 0:  # No permitir valores negativos
                self.counter.value -= 1
        self.conn.send((MSG_DIODE_DEC, ""))
    
    def run(self):
        set_realtime_priority(RT_PRIORITY_EMERGENCY)
        self.setup_callbacks()
        while True:
            time.sleep(1)

def normal_task(conn):
    set_realtime_priority(RT_PRIORITY_NORMAL)
    while True:
        conn.send((MSG_DISPLAY, f"Uptime: {time.monotonic():.1f}s"))
        time.sleep(1)

def cleanup(display, led):
    display.clear_display()
    display.device.cleanup()
    led.off()

if __name__ == "__main__":
    # Configuración de comunicación
    display_conn, interrupt_conn = Pipe()
    
    # Variables compartidas
    counter = Value('i', 0)  # Contador compartido (entero con signo)
    led_emergency = LED(LED_ROJO)
    
    # Crear instancias
    display = DisplayManager(display_conn, counter)
    interrupt = InterruptManager(interrupt_conn, counter, led_emergency)
    
    # Configurar procesos
    processes = [
        Process(target=display.run),
        Process(target=interrupt.run),
        Process(target=normal_task, args=(display_conn,))
    ]
    
    # Iniciar procesos con prioridades
    for i, proc in enumerate(processes):
        proc.start()
        #cpu_affinity = {i % 2}
        cpu_affinity = {0}
        os.sched_setaffinity(proc.pid, cpu_affinity)
        
        if i == 0:  # Display
            os.sched_setscheduler(proc.pid, os.SCHED_FIFO, 
                                os.sched_param(RT_PRIORITY_DISPLAY))
        elif i == 1:  # Interrupciones
            os.sched_setscheduler(proc.pid, os.SCHED_FIFO, 
                                os.sched_param(RT_PRIORITY_EMERGENCY))
        else:  # Normal
            os.sched_setscheduler(proc.pid, os.SCHED_FIFO, 
                                os.sched_param(RT_PRIORITY_NORMAL))
    
    # Manejo de señales
    signal.signal(signal.SIGINT, lambda s, f: cleanup(display, led_emergency))
    signal.signal(signal.SIGTERM, lambda s, f: cleanup(display, led_emergency))
    
    try:
        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        cleanup(display, led_emergency)
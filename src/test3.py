import os
import time
from multiprocessing import Process, Value, Lock
from gpiozero import Button, LED
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from luma.core.render import canvas
import signal

# Configuración
RT_PRIORITY_EMERGENCY = 99
RT_PRIORITY_DISPLAY = 50

EMERGENCY_BTN_PIN = 22
DIODE_INC_PIN = 17
DIODE_DEC_PIN = 27
LED_EMERGENCY_PIN = 5

def set_realtime_priority(priority):
    try:
        param = os.sched_param(priority)
        os.sched_setscheduler(0, os.SCHED_FIFO, param)
    except PermissionError:
        print("Ejecuta como root para prioridad RT!")

class OLEDManager:
    def __init__(self, counter, lock):
        self.counter = counter
        self.lock = lock
        self.running = True
        self.device = ssd1306(i2c(port=1, address=0x3C))
        self.clear_display()
        
    def clear_display(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, fill="black")

    def update_display(self):
        while self.running:
            with self.lock:  # Usar el mismo lock que para el contador
                current_count = self.counter.value
                
            with canvas(self.device) as draw:
                draw.text((0, 0), f"Contador: {current_count}", fill="white")
                draw.text((0, 20), "Estado: Operativo", fill="white")
            time.sleep(0.1)  # Actualización más rápida

    def run(self):
        set_realtime_priority(RT_PRIORITY_DISPLAY)
        self.update_display()

class InterruptHandler:
    def __init__(self, counter, lock, led):
        self.counter = counter
        self.lock = lock
        self.led = led
        self.setup_gpio()

    def setup_gpio(self):
        # Configuración hardware con debounce
        self.emergency_btn = Button(EMERGENCY_BTN_PIN, bounce_time=0.1)
        self.diode_inc = Button(DIODE_INC_PIN, bounce_time=0.05)
        self.diode_dec = Button(DIODE_DEC_PIN, bounce_time=0.05)
        
        # Callbacks
        self.emergency_btn.when_pressed = self.emergency_on
        self.emergency_btn.when_released = self.emergency_off
        self.diode_inc.when_pressed = self.increment
        self.diode_dec.when_pressed = self.decrement

    def emergency_on(self):
        self.led.on()

    def emergency_off(self):
        self.led.off()

    def increment(self):
        with self.lock:
            self.counter.value += 1

    def decrement(self):
        with self.lock:
            if self.counter.value > 0:
                self.counter.value -= 1

    def run(self):
        set_realtime_priority(RT_PRIORITY_EMERGENCY)
        while True:
            time.sleep(1)

def main():
    try:
        # Recursos compartidos
        counter = Value('i', 0)
        lock = Lock()
        led = LED(LED_EMERGENCY_PIN)
        
        # Inicializar OLED
        oled = OLEDManager(counter, lock)
        
        # Procesos
        processes = [
            Process(target=oled.run),
            Process(target=InterruptHandler(counter, lock, led).run)
        ]
        
        # Configurar prioridades
        for p in processes:
            p.start()
        
        # Configurar afinidad de CPU
        os.sched_setaffinity(processes[0].pid, {0})
        os.sched_setaffinity(processes[1].pid, {1})
        
        # Manejar señales de terminación
        signal.signal(signal.SIGINT, lambda s, f: [p.terminate() for p in processes])
        signal.pause()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        led.off()
        oled.clear_display()
        os._exit(0)

if __name__ == "__main__":
    main()
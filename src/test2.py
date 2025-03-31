import os
import time
from multiprocessing import Process, Pipe, Queue, Value
from gpiozero import Button, LED
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from luma.core.render import canvas
import signal

# Constantes para mensajes
MSG_EMERGENCY = 1
MSG_DIODE_INC = 2
MSG_DIODE_DEC = 3
MSG_DISPLAY = 4

# Configuración de prioridades
RT_PRIORITY_EMERGENCY = 99
RT_PRIORITY_DISPLAY = 50
RT_PRIORITY_NORMAL = 1

# Configuración de pines
EMERGENCY_BTN_PIN = 22
DIODE_INC_PIN = 17
DIODE_DEC_PIN = 27
LED_EMERGENCY_PIN = 5

def set_realtime_priority(priority):
    """Configura prioridad SCHED_FIFO para el proceso actual"""
    try:
        param = os.sched_param(priority)
        os.sched_setscheduler(0, os.SCHED_FIFO, param)
    except PermissionError:
        print("Warning: No se pudieron establecer prioridades RT (¿ejecutando como root?)")

class DisplayManager:
    def __init__(self, conn, counter_queue):
        self.conn = conn
        self.counter_queue = counter_queue
        self.counter = 0
        try:
            self.serial = i2c(port=1, address=0x3C)
            self.device = ssd1306(self.serial)
            self.clear_display()
            self.update_display(MSG_DISPLAY, "Iniciando...")
        except Exception as e:
            print(f"Error al inicializar OLED: {e}")
            exit(1)

    def clear_display(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")

    def update_display(self, msg_type, data):
        try:
            # Actualizar contador desde la Queue si hay nuevos valores
            while not self.counter_queue.empty():
                self.counter = self.counter_queue.get_nowait()
            
            with canvas(self.device) as draw:
                draw.text((0, 0), f"Contador: {self.counter}", fill="white")
                
                if msg_type == MSG_EMERGENCY:
                    draw.text((0, 10), "!EMERGENCIA!", fill="white")
                    draw.text((0, 20), data, fill="white")
                elif msg_type == MSG_DIODE_INC:
                    draw.text((0, 10), "↑ Incrementado", fill="white")
                elif msg_type == MSG_DIODE_DEC:
                    draw.text((0, 10), "↓ Decrementado", fill="white")
                elif msg_type == MSG_DISPLAY:
                    draw.text((0, 20), data, fill="white")
        except Exception as e:
            print(f"Error al actualizar display: {e}")

    def run(self):
        set_realtime_priority(RT_PRIORITY_DISPLAY)
        while True:
            if self.conn.poll(0.1):  # Mayor timeout para evitar carga excesiva
                msg_type, data = self.conn.recv()
                self.update_display(msg_type, data)
            else:
                # Actualización periódica
                self.update_display(MSG_DISPLAY, "Funcionando")

class InterruptManager:
    def __init__(self, conn, counter_queue, led_emergency):
        self.conn = conn
        self.counter_queue = counter_queue
        self.led_emergency = led_emergency
        self.counter = 0
        
        try:
            self.emergency_btn = Button(EMERGENCY_BTN_PIN, hold_time=0.1)
            self.diode_inc = Button(DIODE_INC_PIN, bounce_time=0.05)
            self.diode_dec = Button(DIODE_DEC_PIN, bounce_time=0.05)
        except Exception as e:
            print(f"Error al configurar GPIO: {e}")
            exit(1)

    def setup_callbacks(self):
        self.emergency_btn.when_pressed = self.emergency_callback
        self.emergency_btn.when_released = self.emergency_released
        self.diode_inc.when_pressed = self.increment_counter
        self.diode_dec.when_pressed = self.decrement_counter

    def emergency_callback(self):
        try:
            self.led_emergency.on()
            self.conn.send((MSG_EMERGENCY, "Sistema detenido"))
        except Exception as e:
            print(f"Error en callback de emergencia: {e}")

    def emergency_released(self):
        try:
            self.led_emergency.off()
        except Exception as e:
            print(f"Error al liberar emergencia: {e}")

    def increment_counter(self):
        try:
            self.counter += 1
            self.counter_queue.put(self.counter)
            self.conn.send((MSG_DIODE_INC, ""))
        except Exception as e:
            print(f"Error al incrementar contador: {e}")

    def decrement_counter(self):
        try:
            if self.counter > 0:
                self.counter -= 1
                self.counter_queue.put(self.counter)
                self.conn.send((MSG_DIODE_DEC, ""))
        except Exception as e:
            print(f"Error al decrementar contador: {e}")

    def run(self):
        set_realtime_priority(RT_PRIORITY_EMERGENCY)
        self.setup_callbacks()
        while True:
            time.sleep(1)

def normal_task(conn):
    set_realtime_priority(RT_PRIORITY_NORMAL)
    while True:
        try:
            conn.send((MSG_DISPLAY, time.strftime("%H:%M:%S")))
            time.sleep(1)
        except Exception as e:
            print(f"Error en tarea normal: {e}")
            time.sleep(1)

def cleanup(display, led_emergency):
    try:
        display.clear_display()
        display.device.cleanup()
        led_emergency.off()
    except Exception as e:
        print(f"Error en limpieza: {e}")
    finally:
        os._exit(0)

def main():
    try:
        # Configuración de comunicación
        display_conn, interrupt_conn = Pipe()
        counter_queue = Queue()
        
        # Inicializar LED
        led_emergency = LED(LED_EMERGENCY_PIN)
        
        # Crear instancias
        display = DisplayManager(display_conn, counter_queue)
        interrupt = InterruptManager(interrupt_conn, counter_queue, led_emergency)
        
        # Configurar procesos
        processes = [
            Process(target=display.run),
            Process(target=interrupt.run),
            Process(target=normal_task, args=(display_conn,))
        ]
        
        # Iniciar procesos
        for i, proc in enumerate(processes):
            proc.start()
            try:
                #os.sched_setaffinity(proc.pid, {i % 2})
                os.sched_setaffinity(proc.pid, {0})
                
                if i == 0:  # Display
                    os.sched_setscheduler(proc.pid, os.SCHED_FIFO, os.sched_param(RT_PRIORITY_DISPLAY))
                elif i == 1:  # Interrupciones
                    os.sched_setscheduler(proc.pid, os.SCHED_FIFO, os.sched_param(RT_PRIORITY_EMERGENCY))
                else:  # Normal
                    os.sched_setscheduler(proc.pid, os.SCHED_FIFO, os.sched_param(RT_PRIORITY_NORMAL))
            except Exception as e:
                print(f"Error al configurar proceso {i}: {e}")
        
        # Manejo de señales
        signal.signal(signal.SIGINT, lambda s, f: cleanup(display, led_emergency))
        signal.signal(signal.SIGTERM, lambda s, f: cleanup(display, led_emergency))
        
        # Esperar finalización
        for proc in processes:
            proc.join()
            
    except Exception as e:
        print(f"Error en main: {e}")
    finally:
        cleanup(display, led_emergency)

if __name__ == "__main__":
    main()
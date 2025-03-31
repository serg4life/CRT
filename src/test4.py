import os
import time
import RPi.GPIO as GPIO
from multiprocessing import Process, Value
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from luma.core.render import canvas
import signal

# Configuración de pines
INC_PIN = 27    # Botón incremento (flanco de subida)
DEC_PIN = 17    # Botón decremento (flanco de subida)
EMERGENCY_PIN = 2  # Botón emergencia (activo bajo)
LED_PIN = 5    # LED de emergencia

# Configurar GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(INC_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DEC_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(EMERGENCY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

# Configurar OLED
serial = i2c(port=1, address=0x3C)
oled = ssd1306(serial)
counter = Value('i', 0)
running = True

def set_realtime_priority():
    """Establece prioridad máxima en tiempo real"""
    param = os.sched_param(os.sched_get_priority_max(os.SCHED_FIFO))
    os.sched_setscheduler(0, os.SCHED_FIFO, param)

def update_display():
    """Proceso para actualizar la pantalla OLED"""
    while running:
        with canvas(oled) as draw:
            draw.text((0, 0), f"Contador: {counter.value}", fill="white")
        time.sleep(0.1)  # 10 FPS

def increment_callback(channel):
    """Callback para incrementar contador"""
    with counter.get_lock():
        counter.value += 1

def decrement_callback(channel):
    """Callback para decrementar contador"""
    with counter.get_lock():
        if counter.value > 0:
            counter.value -= 1

def emergency_callback(channel):
    """Callback para emergencia (activo bajo)"""
    GPIO.output(LED_PIN, GPIO.input(EMERGENCY_PIN))

def setup_interrupts():
    """Configura interrupciones por hardware"""
    # Detección de flanco de subida para incremento/decremento
    GPIO.add_event_detect(INC_PIN, GPIO.FALLING, 
                        callback=increment_callback, 
                        bouncetime=100)  # Debounce de 100ms
    
    GPIO.add_event_detect(DEC_PIN, GPIO.FALLING,
                        callback=decrement_callback,
                        bouncetime=100)
    
    # Detección de cambios para emergencia (activo bajo)
    GPIO.add_event_detect(EMERGENCY_PIN, GPIO.FALLING,
                        callback=emergency_callback,
                        bouncetime=100)

def cleanup(signum, frame):
    """Limpieza al terminar el programa"""
    global running
    running = False
    
    oled.clear()
    GPIO.cleanup()
    os._exit(0)

def main():
    """Función principal"""
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Configurar interrupciones
        setup_interrupts()
        
        # Proceso para actualizar display
        p_display = Process(target=update_display)
        p_display.start()
        
        # Establecer prioridad en tiempo real
        set_realtime_priority()
        
        print("Sistema iniciado. Presiona Ctrl+C para salir.")
        
        # Mantener el programa activo
        while running:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup(None, None)

if __name__ == "__main__":
    main()
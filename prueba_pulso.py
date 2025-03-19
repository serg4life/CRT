import RPi.GPIO as GPIO
import time

# Configura el modo de los pines (BCM o BOARD)
GPIO.setmode(GPIO.BCM)

# Define el pin GPIO que vas a usar
pin_entrada = 27

# Configura el pin como entrada
GPIO.setup(pin_entrada, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

try:
    print("Esperando un pulso alto (1) en el GPIO {}...".format(pin_entrada))
    while True:
        # Lee el estado del pin
        estado = GPIO.input(pin_entrada)
        
        # Si se detecta un 1 (nivel alto), imprime un mensaje
        if estado == GPIO.HIGH:
            print("¡Pulso alto detectado!")
        else:
            print("GONORREA")        
        # Pequeña pausa para evitar sobrecargar la CPU
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Programa terminado por el usuario.")

finally:
    # Limpia los pines GPIO al salir
    GPIO.cleanup()

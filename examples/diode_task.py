import RPi.GPIO as GPIO
import time

# Configura el modo de los pines (BCM o BOARD)
GPIO.setmode(GPIO.BCM)

# Define el pin GPIO que vas a usar
pin_entrada_1 = 27
#pin_entrada_2 = 17

# Configura el pin como entrada con una resistencia pull-down
GPIO.setup(pin_entrada_1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Variable para evitar múltiples detecciones
pulso_detectado = False

# Función que se ejecuta cuando se detecta un pulso alto
def callback_detectar_pulso(channel):
    global pulso_detectado
    if not pulso_detectado:
        print("¡Pulso alto detectado!")
        pulso_detectado = True
        
# Configura la interrupción para detectar un flanco ascendente (de 0 a 1)
GPIO.add_event_detect(pin_entrada_1, GPIO.RISING, callback=callback_detectar_pulso, bouncetime=200)

try:
    print("Esperando un pulso alto (1) en el GPIO {}...".format(pin_entrada_1))
    while True:
        # Mantén el programa en ejecución
        time.sleep(1)

except KeyboardInterrupt:
    print("Programa terminado por el usuario.")

finally:
    # Limpia los pines GPIO al salir
    GPIO.cleanup()
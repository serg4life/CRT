#!/bin/python3
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from time import sleep

# Inicializa la comunicación I²C y el dispositivo OLED
serial = i2c(port=1, address=0x3C)  # El address puede ser 0x3C o 0x3D, depende del display
device = ssd1306(serial)

# Limpia la pantalla
device.clear()

# Dibuja un mensaje en la pantalla
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="white", fill="black")
    draw.text((10, 20), "¡Hola, OLED!", fill="white")

# Espera 5 segundos antes de terminar
sleep(5)
device.clear()

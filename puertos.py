import serial
import time
from playsound import playsound  # Importa playsound

# Configura el nombre del puerto y la tasa de baudios
puerto = '/dev/ttyUSB0'
baudios = 9600

# Intenta abrir el puerto serie
try:
    ser = serial.Serial(puerto, baudios, timeout=1)
    print(f"Conectado al puerto {puerto}")

    estado_anterior_cts = ser.cts
    contador = 0  # Inicializa un contador para los mensajes

    try:
        while True:
            estado_actual_cts = ser.cts

            if estado_anterior_cts and not estado_actual_cts:
                contador += 1  # Incrementa el contador
                print(f"{contador}. Transición de CTS: Activo a Inactivo")
                playsound('/home/ppt/AppGestion/beep-02.mp3')  # Reproduce el sonido

            estado_anterior_cts = estado_actual_cts
            time.sleep(0.1)  # Espera un poco antes de leer nuevamente

    except KeyboardInterrupt:
        print("Programa interrumpido por el usuario")

finally:
    ser.close()
    print("Puerto serie cerrado")


import cv2
import os
from datetime import datetime
import time

def tomar_foto(numero):
    # Inicializar la cámara
    cap = cv2.VideoCapture(0)  # 0 indica la cámara predeterminada

    # Capturar una imagen
    ret, frame = cap.read()

    # Generar un nombre de archivo único basado en el número
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nombre_archivo = f"/home/ppt/AppGestion/inferencias/inf_{timestamp}.png"


    # Guardar la imagen
    cv2.imwrite(nombre_archivo, frame)

    # Liberar la cámara
    cap.release()

if __name__ == "__main__":
    # Definir el número total de fotos a tomar
    total_fotos = 10

    for numero in range(1, total_fotos + 1):
        tomar_foto(numero)
        print(f"Foto {numero} tomada. Esperando...")
        time.sleep(8)  # Ajusta el intervalo de tiempo según sea necesario

    print("Todas las fotos han sido tomadas. Saliendo...")


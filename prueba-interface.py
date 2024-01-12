import cv2
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime

class WebcamApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)

        # Inicializar la cámara
        self.cap = cv2.VideoCapture(0)  # 0 indica la cámara predeterminada

        # Crear lienzo para mostrar la imagen de la webcam
        self.canvas_webcam = tk.Canvas(window, width=640, height=480)
        self.canvas_webcam.pack()

        # Crear lienzo para mostrar las últimas tres imágenes capturadas
        self.canvas_images = tk.Canvas(window, width=640, height=240)
        self.canvas_images.pack()

        # Botón para capturar la imagen de la webcam
        capture_btn = tk.Button(window, text="Capturar", command=self.capture_image)
        capture_btn.pack(pady=10)

        # Lista para almacenar las últimas tres imágenes capturadas
        self.last_captured_images = []
        self.image_titles = []  # Lista para almacenar los títulos de las imágenes

        # Actualizar la imagen de la webcam en el lienzo
        self.update_webcam()

    def update_webcam(self):
        # Capturar un frame de la webcam
        ret, frame = self.cap.read()

        if ret:
            # Convertir el frame de OpenCV a formato compatible con tkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)

            img_tk = ImageTk.PhotoImage(image=img)

            # Mostrar la imagen en el lienzo de la webcam
            self.canvas_webcam.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas_webcam.img = img_tk  # Conservar una referencia para evitar la recolección de basura

        # Actualizar la imagen de la webcam periódicamente (cada 10 ms)
        self.window.after(10, self.update_webcam)

    def capture_image(self):
        # Capturar un frame de la webcam
        ret, frame = self.cap.read()

        if ret:
            # Convertir el frame de OpenCV a formato compatible con tkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)

            # Reducir el tamaño de la imagen al 25%
            img = img.resize((int(img.width * 0.25), int(img.height * 0.25)))

            img_tk = ImageTk.PhotoImage(image=img)

            # Obtener el timestamp actual como título
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Agregar la imagen y el timestamp a la lista
            self.last_captured_images.append((img_tk, timestamp))

            # Mantener solo las últimas tres imágenes
            if len(self.last_captured_images) > 3:
                self.last_captured_images.pop(0)

            # Actualizar el lienzo de imágenes con las últimas tres imágenes y títulos
            self.update_images_canvas()

    def update_images_canvas(self):
        # Limpiar el lienzo de imágenes
        self.canvas_images.delete("all")

        # Mostrar las últimas tres imágenes y títulos en el lienzo de imágenes
        for i, (img_tk, title) in enumerate(self.last_captured_images):
            x_offset = i * 213  # Ajustar la posición horizontal de cada imagen (213 es el ancho después de reducir al 25%)
            self.canvas_images.create_image(x_offset, 0, anchor=tk.NW, image=img_tk)

            # Mostrar el título debajo de cada imagen
            self.canvas_images.create_text(x_offset + 10, 160, anchor=tk.W, text=title)

if __name__ == "__main__":
    root = tk.Tk()
    app = WebcamApp(root, "Webcam App")
    root.mainloop()

    # Liberar la cámara al cerrar la aplicación
    app.cap.release()


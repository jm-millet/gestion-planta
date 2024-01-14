import cv2
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
import mysql.connector

# Conexión a la base de datos
conexion = mysql.connector.connect(
    host="localhost",
    user="operario",
    password="oper24",
    database="bbdd_imagenes"
)

# Crear un cursor para ejecutar consultas
cursor = conexion.cursor()

# Función para insertar un registro en la base de datos
def insertar_registro(nombre_archivo, estado):
    timestamp = datetime.now()
    print(f"Insertando registro en la base de datos:")
    print(f"Timestamp: {timestamp}")
    print(f"Nombre de archivo: {nombre_archivo}")
    print(f"Estado: {estado}")

    insert_sql = """
    INSERT INTO tabla_imagenes (timestamp, nombre_archivo, estado) VALUES (%s, %s, %s)
    """
    datos_registro = (timestamp, nombre_archivo, estado)
    cursor.execute(insert_sql, datos_registro)
    conexion.commit()


class WebcamApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)

        self.cap = cv2.VideoCapture(0)
        # Título de la imagen en directo
        self.label_titulo_webcam = tk.Label(self.window, text="IMAGEN EN DIRECTO", font=("Helvetica", 14))
        self.label_titulo_webcam.pack()

        # Lienzo para mostrar la imagen de la webcam
        self.canvas_webcam = tk.Canvas(window, width=640, height=480)
        self.canvas_webcam.pack()

           # Título de las últimas imágenes capturadas
        self.label_titulo_imagenes = tk.Label(self.window, text="ÚLTIMAS IMÁGENES CAPTURADAS", font=("Helvetica", 14))
        self.label_titulo_imagenes.pack()

        # Lienzo para mostrar las últimas imágenes capturadas
        self.canvas_images = tk.Canvas(window, width=640, height=240)
        self.canvas_images.pack()

        self.capture_btn = tk.Button(window, text="Capturar", command=self.capture_image)
        self.capture_btn.pack(pady=10)

        self.btn_revisar = tk.Button(window, text="Revisar", command=self.open_image_viewer)
        self.btn_revisar.pack(pady=10)

        # Lista para almacenar las últimas tres imágenes capturadas
        self.last_captured_images = []
        self.image_titles = []  

        self.update_webcam()
        
        # Botón para salir de la aplicación
        exit_btn = tk.Button(window, text="Salir", command=self.exit_application)
        exit_btn.pack(side=tk.BOTTOM, pady=10)
        
        

    def update_webcam(self):
        ret, frame = self.cap.read()

        if ret:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)

            img_tk = ImageTk.PhotoImage(image=img)

            self.canvas_webcam.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas_webcam.img = img_tk  

        self.window.after(10, self.update_webcam)

    def capture_image(self):
        ret, frame = self.cap.read()

        if ret:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nombre_archivo = f"/home/ppt/AppGestion/inferencias/inf_{timestamp}.png"

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)

            cv2.imwrite(nombre_archivo, frame)

            estado = "OK"
            insertar_registro(nombre_archivo, estado)

            img = img.resize((int(img.width * 0.25), int(img.height * 0.25)))
            img_tk = ImageTk.PhotoImage(image=img)

            self.last_captured_images.append((img_tk, timestamp))

            if len(self.last_captured_images) > 3:
                self.last_captured_images.pop(0)

            self.update_images_canvas()

    def update_images_canvas(self):
        self.canvas_images.delete("all")

        for i, (img_tk, title) in enumerate(self.last_captured_images):
            x_offset = i * 213
            self.canvas_images.create_image(x_offset, 0, anchor=tk.NW, image=img_tk)
            self.canvas_images.create_text(x_offset + 10, 160, anchor=tk.W, text=title)

    def open_image_viewer(self):
        # Ocultar la ventana actual
        self.window.withdraw()
        # Crear una nueva ventana para ImageViewerApp
        window_viewer = tk.Toplevel(self.window)
        window_viewer.title("Image Viewer")
        ImageViewerApp(window_viewer, "Image Viewer", self)

    def exit_application(self):
        # Liberar la cámara al cerrar la aplicación
        self.cap.release()
        # Cerrar la aplicación
        self.window.destroy()


class ImageViewerApp:
    def __init__(self, window, window_title, webcam_app):
        self.window = window
        self.window.title(window_title)

        self.webcam_app = webcam_app

        self.cursor = conexion.cursor()

        self.cursor.execute("SELECT nombre_archivo, timestamp FROM tabla_imagenes ORDER BY timestamp DESC LIMIT 1")
        self.current_image = self.cursor.fetchone()

        self.show_image()

        btn_atras = tk.Button(window, text="Atrás", command=self.show_previous_image)
        btn_atras.pack(side=tk.LEFT, padx=10)

        btn_adelante = tk.Button(window, text="Adelante", command=self.show_next_image)
        btn_adelante.pack(side=tk.RIGHT, padx=10)

        btn_cerrar = tk.Button(window, text="Cerrar", command=self.close_window)
        btn_cerrar.pack(side=tk.BOTTOM, pady=10)

    def show_image(self):
        if self.current_image:
            nombre_archivo, timestamp = self.current_image

            # Obtener el estado (clasificación) de la imagen desde la base de datos
            self.cursor.execute("SELECT estado FROM tabla_imagenes WHERE nombre_archivo = %s", (nombre_archivo,))
            estado_result = self.cursor.fetchone()

            if estado_result:
                estado = estado_result[0]

                img = Image.open(nombre_archivo)
                img = img.resize((640, 480))
                img_tk = ImageTk.PhotoImage(img)

                if hasattr(self, "label_imagen"):
                    self.label_imagen.destroy()
                self.label_imagen = tk.Label(self.window, image=img_tk)
                self.label_imagen.image = img_tk
                self.label_imagen.pack()

                if hasattr(self, "label_titulo"):
                    self.label_titulo.destroy()
                self.label_titulo = tk.Label(self.window, text=timestamp)
                self.label_titulo.pack()

                # Mostrar la clasificación debajo de la imagen
                if hasattr(self, "label_clasificacion"):
                    self.label_clasificacion.destroy()
                self.label_clasificacion = tk.Label(self.window, text=f"Clasificación = {estado}")
                self.label_clasificacion.pack()

    def show_previous_image(self):
        # Fetch y mostrar la imagen anterior
        self.cursor.execute(
            "SELECT nombre_archivo, timestamp FROM tabla_imagenes WHERE timestamp < %s ORDER BY timestamp DESC LIMIT 1",
            (self.current_image[1],))
        previous_image = self.cursor.fetchone()

        if previous_image:
            self.current_image = previous_image
            self.show_image()

        # Limpiar el cursor
        self.cursor.fetchall()

    def show_next_image(self):
        # Fetch y mostrar la siguiente imagen
        self.cursor.execute(
            "SELECT nombre_archivo, timestamp FROM tabla_imagenes WHERE timestamp > %s ORDER BY timestamp ASC LIMIT 1",
            (self.current_image[1],))
        next_image = self.cursor.fetchone()

        if next_image:
            self.current_image = next_image
            self.show_image()

        # Limpiar el cursor
        self.cursor.fetchall()

    def close_window(self):
        self.window.destroy()
        self.window = None  # Eliminar referencia a la ventana
        # Mostrar la ventana principal de la aplicación (WebcamApp)
        self.webcam_app.window.deiconify()


if __name__ == "__main__":
    root = tk.Tk()
    app_webcam = WebcamApp(root, "Webcam App")
    root.mainloop()


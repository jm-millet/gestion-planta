import cv2
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
import mysql.connector

import grpc
from edge_agent_pb2_grpc import EdgeAgentStub
import edge_agent_pb2 as pb2
import time

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

# Función arrancar modelo

model_name = "CM-coches"
model_component_name = model_name 

def start_model_if_needed(stub, model_name):
    # Starting model if needed.
    while True:
        model_description_response = stub.DescribeModel(pb2.DescribeModelRequest(model_component=model_name))
        print(f"DescribeModel() returned {model_description_response}")
        if model_description_response.model_description.status == pb2.RUNNING:
            print("Model is already running.")
            break
        elif model_description_response.model_description.status == pb2.STOPPED:
            print("Starting the model.")
            stub.StartModel(pb2.StartModelRequest(model_component=model_name))
            continue
        elif model_description_response.model_description.status == pb2.FAILED:
            raise Exception(f"model {model_name} failed to start")
        print(f"Waiting for model to start.")
        if model_description_response.model_description.status != pb2.STARTING:
            break
        time.sleep(1.0)


# Detecting anomalies.
def detect_anomalies(stub, model_name, image_path):
    image = Image.open(image_path)
    image = image.convert("RGB")
    detect_anomalies_response = stub.DetectAnomalies(
        pb2.DetectAnomaliesRequest(
            model_component=model_name,
            bitmap=pb2.Bitmap(
                width=image.size[0],
                height=image.size[1],
                byte_data=bytes(image.tobytes())
            ) 
        )
    )
    if detect_anomalies_response.detect_anomaly_result.is_anomalous:
     	print ("COCHE MALO")
    else:
    	print ("COCHE BUENO") 
    #print(f"Image is anomalous - {detect_anomalies_response.detect_anomaly_result.is_anomalous}")
    return detect_anomalies_response.detect_anomaly_result





class WebcamApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.stub = stub 

        self.cap = cv2.VideoCapture(0)
        
        # ... (Inicialización de la aplicación)
        self.last_captured_images = []  # Para almacenar imágenes capturadas y su metadata
        
        
        # Título de la imagen en directo
        self.label_titulo_webcam = tk.Label(self.window, text="IMAGEN EN DIRECTO", font=("Helvetica", 14))
        self.label_titulo_webcam.pack()

        # Lienzo para mostrar la imagen de la webcam
        self.canvas_webcam = tk.Canvas(window, width=640, height=480)
        self.canvas_webcam.pack()

        # Adding blank line separators
        for _ in range(3):
            separator = tk.Label(window, text="", height=1)  # Height=1 for a single blank line
            separator.pack()


        # Título de las últimas imágenes capturadas
        self.label_titulo_imagenes = tk.Label(window, text="ÚLTIMAS IMÁGENES CAPTURADAS", font=("Helvetica", 14))
        self.label_titulo_imagenes.pack()

        # Frame for the canvas
        frame_canvas = tk.Frame(window, bd=2, relief=tk.SUNKEN)
        frame_canvas.pack()

        # Lienzo para mostrar las últimas imágenes capturadas
        self.canvas_images = tk.Canvas(frame_canvas, width=640, height=240)
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

            detect_anomalies_result = detect_anomalies(self.stub, model_component_name, nombre_archivo)
            
            # Llamada a detect_anomalies y asignación del resultado a detect_anomalies_result
            detect_anomalies_result = detect_anomalies(stub, model_component_name, nombre_archivo)

            # Usar detect_anomalies_result para verificar si hay una anomalía        
            if detect_anomalies_result.is_anomalous:
                estado = "KO"
            else:
                estado = "OK"

            
#            estado = "OK"  # O cualquier lógica para determinar el estado
            insertar_registro(nombre_archivo, estado)

            img = img.resize((int(img.width * 0.25), int(img.height * 0.25)))
            img_tk = ImageTk.PhotoImage(image=img)

            self.last_captured_images.append((img_tk, timestamp, estado))  # Añadir estado

            if len(self.last_captured_images) > 3:
                self.last_captured_images.pop(0)

            self.update_images_canvas()

    
    def update_images_canvas(self):
        self.canvas_images.delete("all")

        for i, (img_tk, title, estado) in enumerate(self.last_captured_images):
            x_offset = i * 213  # Ajusta este valor según sea necesario para el espaciado

            # Coordenadas para el marco
            x0, y0 = x_offset, 0
            x1, y1 = x_offset + img_tk.width(), img_tk.height()

            # Crear el marco dependiendo del estado
            if estado == "KO":
                self.canvas_images.create_rectangle(x0, y0, x1, y1, outline="red", width=8)
            else:  # Suponiendo que el otro estado es "OK"
                self.canvas_images.create_rectangle(x0, y0, x1, y1, outline="blue", width=8)

            # Mostrar la imagen
            self.canvas_images.create_image(x_offset, 0, anchor=tk.NW, image=img_tk)
            # Mostrar el título y el estado
            self.canvas_images.create_text(x_offset + 10, 160, anchor=tk.W, text=title)
            self.canvas_images.create_text(x_offset + 10, 180, anchor=tk.W, text=f"Estado: {estado}")

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
        # Cerrar la conexión a la base de datos
        conexion.close()
        # Cerrar la aplicación
        self.window.destroy()
        channel.close()  # Cierra el canal al salir de la aplicación

class ImageViewerApp:
    def __init__(self, window, window_title, webcam_app):
        self.window = window
        self.window.title(window_title)
        self.webcam_app = webcam_app
        self.conexion = conexion
        self.cursor = self.conexion.cursor()
        
        self.current_estado = None
        self.current_nombre_archivo = None
        self.current_timestamp = None

        # Crear la tabla tabla_correcciones si no existe
        self.create_correction_table()

        # Agregar elementos de UI y organizarlos
        self.setup_ui()

        try:
            self.cursor.execute("SELECT nombre_archivo, timestamp FROM tabla_imagenes ORDER BY timestamp DESC LIMIT 1")
            self.current_image = self.cursor.fetchone()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.current_image = None

        self.show_image()

    def setup_ui(self):
        # Agrega aquí la creación y disposición de tus botones y otros elementos de UI

        btn_atras = tk.Button(self.window, text="Atrás", command=self.show_previous_image)
        btn_atras.pack(side=tk.LEFT, padx=10)

        btn_adelante = tk.Button(self.window, text="Adelante", command=self.show_next_image)
        btn_adelante.pack(side=tk.RIGHT, padx=10)

        self.label_form_title = tk.Label(self.window, text="Corrección clasificación:", font=("Helvetica", 12))
        self.label_form_title.pack()

        self.classification_var = tk.StringVar(value="OK")

        self.radio_ok = tk.Radiobutton(self.window, text="OK", variable=self.classification_var, value="OK")
        self.radio_ok.pack()

        self.radio_ko = tk.Radiobutton(self.window, text="KO", variable=self.classification_var, value="KO")
        self.radio_ko.pack()

        self.btn_submit = tk.Button(self.window, text="Corregir", command=self.submit_classification)
        self.btn_submit.pack(pady=10)

        btn_cerrar = tk.Button(self.window, text="Cerrar", command=self.close_window)
        btn_cerrar.pack(side=tk.BOTTOM, pady=10)

    def create_correction_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS tabla_correcciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp_original DATETIME,
            timestamp_correccion DATETIME,
            estado_original ENUM("OK", "KO") NOT NULL,
            estado_corregido ENUM("OK", "KO") NOT NULL,
            nombre_fichero VARCHAR(255)
        )
        """
        self.cursor.execute(create_table_sql)
        self.conexion.commit()
    
    
    def submit_classification(self):
        selected_value = self.classification_var.get()
        timestamp_correccion = datetime.now()

        insert_sql = """
        INSERT INTO tabla_correcciones (timestamp_original, timestamp_correccion, estado_original, estado_corregido, nombre_fichero) 
        VALUES (%s, %s, %s, %s, %s)
        """
        data = (self.current_timestamp, timestamp_correccion, self.current_estado, selected_value, self.current_nombre_archivo)

        self.cursor.execute(insert_sql, data)
        self.conexion.commit()

        print(f"Clasificación corregida: {selected_value}")
        print(f"Nombre del archivo: {self.current_nombre_archivo}")
        print(f"Timestamp original: {self.current_timestamp}")
        print(f"Estado original: {self.current_estado}")
        print(f"Timestamp de corrección: {timestamp_correccion}")

    def show_image(self):
        if self.current_image:
            self.current_nombre_archivo, self.current_timestamp = self.current_image

            # Obtener el estado (clasificación) de la imagen desde la base de datos
            self.cursor.execute("SELECT estado FROM tabla_imagenes WHERE nombre_archivo = %s", (self.current_nombre_archivo,))
            estado_result = self.cursor.fetchone()

            if estado_result:
                self.current_estado = estado_result[0]

                img = Image.open(self.current_nombre_archivo)
                img = img.resize((640, 480))
                img_tk = ImageTk.PhotoImage(img)

                if hasattr(self, "label_imagen"):
                    self.label_imagen.destroy()
                self.label_imagen = tk.Label(self.window, image=img_tk)
                self.label_imagen.image = img_tk  # Mantener una referencia.
                self.label_imagen.pack()

                if hasattr(self, "label_titulo"):
                    self.label_titulo.destroy()
                self.label_titulo = tk.Label(self.window, text=self.current_timestamp)
                self.label_titulo.pack()

                # Mostrar la clasificación debajo de la imagen
                if hasattr(self, "label_clasificacion"):
                    self.label_clasificacion.destroy()
                self.label_clasificacion = tk.Label(self.window, text=f"Clasificación = {self.current_estado}")
                self.label_clasificacion.pack()
        else:
            # Manejar el caso en que no hay imagen actual.
            if hasattr(self, "label_imagen"):
                self.label_imagen.destroy()
            self.label_imagen = tk.Label(self.window, text="No hay imagen disponible.")
            self.label_imagen.pack()

            if hasattr(self, "label_titulo"):
                self.label_titulo.destroy()
            if hasattr(self, "label_clasificacion"):
                self.label_clasificacion.destroy()

    def show_previous_image(self):
        # Asegúrate de que todos los resultados anteriores han sido leídos
        self.cursor.fetchall()

        # Ejecutar la consulta para obtener la imagen anterior
        self.cursor.execute(
            "SELECT nombre_archivo, timestamp FROM tabla_imagenes WHERE timestamp < %s ORDER BY timestamp DESC LIMIT 1",
            (self.current_timestamp,))
        previous_image = self.cursor.fetchone()

        if previous_image:
            self.current_image = previous_image
            self.show_image()

    def show_next_image(self):
        # Asegúrate de que todos los resultados anteriores han sido leídos
        self.cursor.fetchall()

         # Ejecutar la consulta para obtener la siguiente imagen
        self.cursor.execute(
            "SELECT nombre_archivo, timestamp FROM tabla_imagenes WHERE timestamp > %s ORDER BY timestamp ASC LIMIT 1",
            (self.current_timestamp,))
        next_image = self.cursor.fetchone()

        if next_image:
            self.current_image = next_image
            self.show_image()


    def close_window(self):
        self.window.destroy()
        self.window = None  # Eliminar referencia a la ventana
        # Cierra el canal stub
        #channel.close()
        # Mostrar la ventana principal de la aplicación (WebcamApp)
        self.webcam_app.window.deiconify()
        stop_model()


def stop_model():
    
    #channel = grpc.insecure_channel("unix:///tmp/aws.iot.lookoutvision.EdgeAgent.sock")
    #stub = EdgeAgentStub(channel)
    try:
        result = stub.StopModel(pb2.StopModelRequest(model_component=model_component_name))
        print(result)
    except grpc.RpcError as e:
        print(f"Error invoking StopModel: {e}")
    
    

if __name__ == "__main__":
    
    # Creating stub.
    channel = grpc.insecure_channel("unix:///tmp/aws.iot.lookoutvision.EdgeAgent.sock")
    stub = EdgeAgentStub(channel)
    
    start_model_if_needed(stub, model_name)
    
    root = tk.Tk()
    app_webcam = WebcamApp(root, "Webcam App")
    root.mainloop()
    channel.close()  # Cierra el canal después de que la GUI se cierra


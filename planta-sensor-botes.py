import cv2
import tkinter as tk
from tkinter import ttk  # Import ttk module for styled widgets

from PIL import Image, ImageTk
from datetime import datetime
import mysql.connector

import grpc
from edge_agent_pb2_grpc import EdgeAgentStub
import edge_agent_pb2 as pb2
import time
from playsound import playsound

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime, timedelta

import serial

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

model_name = "ComponBotes"  # Poner que sea configurable
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
    print ("inicio detect") 
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
    print ("fin detect")

    return detect_anomalies_response.detect_anomaly_result





class WebcamApp:
    def __init__(self, master, title):
        self.window = master
        self.window.title(title)
        self.window.configure(background='#3D5965')  # Establecer un color de fondo gris claro
        
        # Vincular el evento de cierre de la ventana con la función exit_application
        self.window.protocol("WM_DELETE_WINDOW", self.exit_application)


        # Definición y empaquetado del Label para el nombre del modelo en la parte superior
        model_name_label = tk.Label(self.window, text=f"NOMBRE DEL MODELO ENTRENADO: {model_name}", bg='#3D5965', fg='#f0f0f0')
        model_name_label.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.cursor = conexion.cursor()

        self.stub = stub 

        self.cap = cv2.VideoCapture(0) # Poner que sea configurable
        
        self.statistics_window = None  # Para saber si la ventana de estadísticas está abierta
        self.statistics_window_on_close = None

        self.update_graph_id = None
        self.update_statistics_id = None


        # Inicializar puerto sensor fotoelectrico
        puerto = '/dev/ttyUSB0' # Poner que sea configurable
        baudios = 9600

        try:
            self.ser = serial.Serial(puerto, baudios, timeout=1)
            print(f"Conectado al puerto {puerto}")
            self.estado_anterior_cts = self.ser.cts
            self.sensor = True

        except serial.SerialException as e:
            print(f"Error al abrir el puerto {puerto}: {e}")
            self.sensor = False
            self.estado_anterior_cts = True
            self.estado_actual_cts = True
            pass
        
        # Inicializar la lista para almacenar las últimas imágenes capturadas
        self.last_captured_images = []
             
        # Diseño con frames para una mejor organización
        top_frame = tk.Frame(self.window, bg='#3D5965')
        top_frame.pack(pady=10)

        # Inicializar para el control de movimiento
        self.last_frame = None
        self.capture_scheduled = False  # Variable para controlar si la captura está programada

        self.label_titulo_webcam = tk.Label(top_frame, text="VIDEO CÁMARA", font=("Helvetica", 14), bg='#3D5965', fg='#f0f0f0')
        self.label_titulo_webcam.pack()

        # Reducir el tamaño del canvas de la webcam a la mitad
        self.canvas_webcam = tk.Canvas(top_frame, width=320, height=240, bd=5, relief="flat")
        self.canvas_webcam.pack()
  
        self.motion_detection_enabled = tk.BooleanVar(value=False)  # Variable para el estado de detección de movimiento

        # Frame para los botones y la casilla de selección
        button_frame = tk.Frame(self.window, bg='#3D5965')
        button_frame.pack(pady=10)

        # Casilla de selección para activar/desactivar la detección de movimiento
        self.checkbox_motion_detection = tk.Checkbutton(button_frame, text="Detección de movimiento", variable=self.motion_detection_enabled, bg='#3D5965', highlightbackground='#3D5965', activebackground='#3D5965')
        self.checkbox_motion_detection.pack(side=tk.LEFT, padx=5)

        # Botones
        self.capture_btn = ttk.Button(button_frame, text="Capturar", command=self.capture_image)
        self.capture_btn.pack(side=tk.LEFT, padx=5)

        self.btn_revisar = ttk.Button(button_frame, text="Revisar", command=self.open_image_viewer)
        self.btn_revisar.pack(side=tk.LEFT, padx=5)

        # Frame para mostrar las últimas imágenes capturadas, situado justo debajo del gráfico
        image_frame = tk.Frame(self.window, bg='#3D5965')
        image_frame.pack(pady=(10, 0), fill=tk.X)

        self.label_titulo_imagenes = tk.Label(image_frame, text="ÚLTIMAS IMÁGENES CAPTURADAS", font=("Helvetica", 14), bg='#3D5965', fg='#f0f0f0')
        self.label_titulo_imagenes.pack()

        self.canvas_images = tk.Canvas(image_frame, width=640, height=180, bg='#3D5965', highlightthickness=0)
        self.canvas_images.pack()



        # Frame para el gráfico de columnas
        graph_frame = tk.Frame(self.window, bg='#3D5965')
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))  # Asegurar que el gráfico se expanda y ocupe la parte superior

        # Creación y configuración del gráfico de columnas
        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.fig.subplots_adjust(bottom=0.2)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Actualización inicial del gráfico
        self.update_graph()

        # Frame contenedor para los botones en la parte inferior de la ventana
        button_frame = tk.Frame(self.window, bg='#3D5965')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 10))  # Posicionamiento al fondo para botones

        # Botón "Abrir Estadísticas"
        self.open_estadisticas_btn = tk.Button(button_frame, text="Abrir Estadísticas", command=self.show_statistics_window)
        self.open_estadisticas_btn.pack(side=tk.LEFT, padx=10, pady=5)

        # Botón "Salir"
        exit_btn = ttk.Button(button_frame, text="Salir", command=self.exit_application)
        exit_btn.pack(side=tk.RIGHT, padx=10, pady=5)

        # Inicialización para la actualización de la webcam
        self.update_webcam()
        
    def fetch_ko_records(self, start_time, end_time):
        """
        Consulta a la base de datos para obtener el número de registros KO
        en un intervalo de tiempo específico.
        """
        query = ("SELECT COUNT(*) FROM tabla_imagenes "
                 "WHERE estado = 'KO' AND "
                 "timestamp BETWEEN %s AND %s")
        self.cursor.execute(query, (start_time, end_time))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def show_statistics_window(self):
        if self.statistics_window is None:
            self.statistics_window = tk.Toplevel(self.window)
            self.statistics_window.title("Estadísticas")

            self.time_shift = 0  # Variable para controlar el desplazamiento en el tiempo

            # Botón para disminuir el desplazamiento del tiempo (mover hacia el presente)
            self.button_decrease_time_shift = tk.Button(self.statistics_window, text="<",
                                                        command=lambda: self.update_time_shift(15))
            self.button_decrease_time_shift.pack(side=tk.LEFT)

            # Botón para aumentar el desplazamiento del tiempo (mover hacia el pasado)
            self.button_increase_time_shift = tk.Button(self.statistics_window, text=">",
                                                        command=lambda: self.update_time_shift(-15))
            self.button_increase_time_shift.pack(side=tk.RIGHT)

            # Crear una nueva figura y canvas para el gráfico de estadísticas
            self.stats_fig, self.stats_ax = plt.subplots(figsize=(8*1.3, 6))
            self.stats_fig.subplots_adjust(bottom=0.3)
            self.stats_fig.patch.set_facecolor('lightgrey')  # Cambiar el color de fondo de la figura a gris
            self.stats_ax.set_facecolor('white')  # Cambiar el color de fondo del área del gráfico a gris
            
            self.stats_canvas = FigureCanvasTkAgg(self.stats_fig, master=self.statistics_window)
            self.stats_canvas.draw()
            self.stats_canvas.get_tk_widget().pack()

            self.update_statistics()  # Llamar directamente para inicializar el gráfico

            def on_close():
                plt.close(self.stats_fig)
                self.statistics_window.destroy()
                self.statistics_window = None

            self.statistics_window.protocol("WM_DELETE_WINDOW", on_close)
        else:
            self.statistics_window.lift()

    def update_time_shift(self, adjustment):
        self.time_shift += adjustment
        if self.time_shift < 0:
            self.time_shift = 0
        self.update_statistics()

    def update_statistics(self):
        if self.statistics_window:
            now = datetime.now() - timedelta(minutes=self.time_shift)
            intervals = [(now - timedelta(minutes=15*(i+1)), now - timedelta(minutes=15*i)) for i in range(15)]
            data = [self.fetch_ko_records(start, end) for start, end in intervals[::-1]]
            tick_labels = [start_time.strftime("%Y-%m-%d %H:%M") for start_time, _ in intervals[::-1]]

            self.stats_ax.clear()
            self.stats_ax.set_facecolor('white')  # Asegurarse de que el color de fondo se aplique también al actualizar
            self.stats_ax.bar(range(len(data)), data, tick_label=tick_labels)
            self.stats_ax.set_xticklabels(tick_labels, rotation=90, ha="right")
            self.stats_ax.set_xlabel("Fecha y Hora")
            self.stats_ax.set_ylabel("Número de Anomalías")
            self.stats_ax.set_title("HISTÓRICO DE ANOMALÍAS")

            self.stats_canvas.draw()
        
    def update_graph(self):
        now = datetime.now()
        start_time = now - timedelta(minutes=15)

        # Preparar un diccionario para almacenar el conteo de imágenes KO por cada minuto
        minute_counts = {minute: 0 for minute in range(-15, 0)}

        cursor = conexion.cursor()
        query = """SELECT COUNT(*) as count, MIN(timestamp)
                   FROM tabla_imagenes
                   WHERE estado = 'KO' AND timestamp BETWEEN %s AND %s
                   GROUP BY YEAR(timestamp), MONTH(timestamp), DAY(timestamp), HOUR(timestamp), MINUTE(timestamp)"""
        cursor.execute(query, (start_time, now))
        data = cursor.fetchall()
        cursor.close()
    
        for count, timestamp in data:
            timestamp = timestamp.replace(second=0, microsecond=0)
            minute_difference = int((timestamp - now).total_seconds() // 60)
            if -15 <= minute_difference < 0:
                minute_counts[minute_difference] = count

        # Preparar datos para el gráfico
        minutes = list(minute_counts.keys())
        counts = list(minute_counts.values())

        # Actualizar gráfico
        self.ax.clear()
        self.ax.bar(minutes, counts, color='green')
        self.ax.set_xlabel('Minutos desde la hora actual')
        self.ax.set_ylabel('Número Fallos')
        self.ax.set_xticks(range(-15, 0))  # Asegurar que se muestren todos los minutos

        # Ejemplo de cómo cambiar los colores en un gráfico
        self.ax.set_facecolor('#f0f0f0')  # Cambia el color de fondo del subplot
        self.fig.set_facecolor('#3D5965')  # Cambia el color de fondo de la figura
        self.ax.xaxis.label.set_color('#f0f0f0')  # Cambia el color de la etiqueta del eje X
        self.ax.yaxis.label.set_color('#f0f0f0')  # Cambia el color de la etiqueta del eje Y
        self.ax.set_title("ANOMALÍAS ÚLTIMOS 15 MINUTOS", color='#f0f0f0')  # Cambia el color del título

        self.canvas.draw()

        # Programar la próxima actualización
        self.update_graph_id = self.window.after(10000, self.update_graph)

    def update_webcam(self):
        
        ret, frame = self.cap.read()

        if ret:
            # Redimensionar la imagen capturada de la webcam a la mitad de su tamaño original
            frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

            #Detección paso por sensor fotoelectrico
            if self.sensor:
                self.estado_actual_cts = self.ser.cts
            if self.estado_anterior_cts and not self.estado_actual_cts:
                print("DETECCIÓN CELULA FOTOELECTRICA")
                playsound('/home/ppt/AppGestion/nice-camera-click-106269.mp3')
                # Llamada a la función de captura de imagen (ajustar según tu código)
                if not self.capture_scheduled:
                    self.window.after(50, self.schedule_capture)  # Programa la captura después de 3 segundos
                    self.capture_scheduled = True
                
            self.estado_anterior_cts = self.estado_actual_cts

            # Convertir a escala de grises para la detección de movimiento
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.motion_detection_enabled.get():
                # Realizar detección de movimiento si la casilla está activada
                if self.last_frame is not None:
                    frame_delta = cv2.absdiff(self.last_frame, gray)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    for contour in contours:
                        if cv2.contourArea(contour) > 500:  # Ajusta este valor según sea necesario
                            print("DETECCIÓN MOVIMIENTO")
                            if not self.capture_scheduled:
                                self.window.after(3000, self.schedule_capture)  # Programa la captura después de 3 segundos
                                self.capture_scheduled = True
                            break

            # Actualizar el último cuadro para la próxima detección
            self.last_frame = gray

            # Mostrar el cuadro redimensionado en la interfaz de usuario
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img_tk = ImageTk.PhotoImage(image=img)
            self.canvas_webcam.create_image(5, 5, anchor=tk.NW, image=img_tk)
            self.canvas_webcam.img = img_tk

            # Agregar la fecha y hora al Canvas
            time_text = self.canvas_webcam.create_text(10, 10, anchor="nw", fill="white", font=("Arial", 10))

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.canvas_webcam.itemconfig(time_text, text=current_time)


            self.update_webcam_id = self.window.after(10, self.update_webcam)


    def schedule_capture(self):
        self.capture_image()
        self.capture_scheduled = False  # Restablecer la variable de control


    def capture_image(self):
        ret, frame = self.cap.read()

        if ret:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nombre_archivo = f"/home/ppt/AppGestion/inferencias/inf_{timestamp}.png"

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)

            cv2.imwrite(nombre_archivo, frame)
         
            # Llamada a detect_anomalies y asignación del resultado a detect_anomalies_result
            detect_anomalies_result = detect_anomalies(stub, model_component_name, nombre_archivo)

            # Usar detect_anomalies_result para verificar si hay una anomalía        
            if detect_anomalies_result.is_anomalous:
                estado = "KO"
                playsound('/home/ppt/AppGestion/beep-02.mp3')
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

        # Añadir una línea encima de las imágenes capturadas
        # self.canvas_images.create_line(0, 10, self.canvas_images.winfo_width(), 10, fill="black")

        for i, (img_tk, title, estado) in enumerate(self.last_captured_images):
            x_offset = i * 213 + 20  # Ajusta este valor según sea necesario para el espaciado

            # Coordenadas para la imagen y el marco
            x_img, y_img = x_offset, 20  # Posición inicial de la imagen ajustada debajo de la línea
            x1, y1 = x_offset + img_tk.width(), y_img + img_tk.height()

            # Crear el marco dependiendo del estado
            if estado == "KO":
                self.canvas_images.create_rectangle(x_img, y_img, x1, y1, outline="red", width=8)
            else:  # Suponiendo que el otro estado es "OK"
                self.canvas_images.create_rectangle(x_img, y_img, x1, y1, outline="blue", width=8)

            # Mostrar la imagen
            self.canvas_images.create_image(x_img, y_img, anchor=tk.NW, image=img_tk)

            # Mostrar el título y el estado con menos espacio debajo de cada imagen
            self.canvas_images.create_text(x_offset + 10, y1 + 15, anchor=tk.W, text=title)
            self.canvas_images.create_text(x_offset + 10, y1 + 30, anchor=tk.W, text=f"Estado: {estado}")

    def open_image_viewer(self):
        # Ocultar la ventana actual
        self.window.withdraw()
        # Crear una nueva ventana para ImageViewerApp
        window_viewer = tk.Toplevel(self.window)
        window_viewer.title("Image Viewer")
        ImageViewerApp(window_viewer, "Image Viewer", self)

    def exit_application(self):
        
        if self.update_graph_id:
            self.window.after_cancel(self.update_graph_id)
        if self.update_statistics_id:
            self.statistics_window.after_cancel(self.update_statistics_id)

        if hasattr(self, 'update_webcam_id'):
                self.window.after_cancel(self.update_webcam_id)

        # Verifica si la ventana de estadísticas está abierta y ciérrala si es necesario.
        if self.statistics_window is not None and callable(self.statistics_window_on_close):
            self.statistics_window_on_close()  # Llama a on_close para cerrar la ventana de estadísticas
        
        if self.statistics_window_on_close is not None and callable(self.statistics_window_on_close):
            self.statistics_window_on_close()

        # Finalizar la aplicación
        self.window.quit()  # Termina el mainloop de Tkinter

        
        # Liberar la cámara al cerrar la aplicación
        self.cap.release()
        # Cerrar la conexión a la base de datos
        conexion.close()
        #Cerrar puerto
        if self.sensor:        
            self.ser.close()
            print("Puerto serie cerrado")

        # Cerrar la aplicación
        self. window.destroy()
        stop_model()
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
 

import sys
import os
import shutil
import json
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton,
    QFileDialog, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon
from Map_generator import generar_mapa_desde_todas_las_subcarpetas

ESTADO_JSON = "estado_app.json"

class MapaApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App con Mapa")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(600, 400)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.estado = {
            "imagenes_cargadas": False,
            "imagen_segundos": [],
            "imagenes_cargadas_labels": False,
            "esperando_coords": False
        }
        self.cargar_estado()

        self.crear_barra_navegacion()
        self.crear_vista_mapa()
        self.verificar_mapa_inicial()

    def guardar_estado(self):
        with open(ESTADO_JSON, "w") as f:
            json.dump(self.estado, f, indent=4)

    def cargar_estado(self):
        if os.path.exists(ESTADO_JSON):
            with open(ESTADO_JSON, "r") as f:
                self.estado = json.load(f)

    def crear_boton_icono(self, ruta, tooltip, callback):
        btn = QToolButton()
        btn.setIcon(QIcon(ruta))
        btn.setIconSize(QSize(30, 30))
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                margin: 5px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }
        """)
        btn.setFixedSize(50, 50)
        btn.clicked.connect(callback)
        return btn

    def crear_barra_navegacion(self):
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(8, 4, 8, 4)
        nav_bar.setSpacing(4)

        btn_cargar = self.crear_boton_icono("assets/icons/map.svg", "Cargar mapa", self.on_cargar_click)
        btn_importar_recorrido = self.crear_boton_icono("assets/icons/file.svg", "Importar Recorrido", self.importar_recorrido)
        btn_extraer_frames = self.crear_boton_icono("assets/icons/image.svg", "Extraer frames", self.extraer_frames_recorrido)
        btn_borrar = self.crear_boton_icono("assets/icons/trash.svg", "Borrar todo", self.borrar_datos)

        for btn in [btn_cargar, btn_importar_recorrido, btn_extraer_frames, btn_borrar]:
            nav_bar.addWidget(btn)

        nav_bar.addStretch()
        nav_container = QWidget()
        nav_container.setLayout(nav_bar)
        nav_container.setStyleSheet("background-color: #2d333b; border-bottom: 2px solid #1f242c;")
        self.layout.addWidget(nav_container)

    def crear_vista_mapa(self):
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view, stretch=1)
        self.mostrar_placeholder_mapa()

    def mostrar_placeholder_mapa(self):
        html_placeholder = """
        <div style='text-align:center; margin-top:100px; color:#ccc; font-family:Segoe UI, sans-serif;'>
            <h2 style='margin-top:20px;'>No hay archivo de mapa cargado</h2>
            <p style='font-size:14px;'>Importa un recorrido para visualizar el mapa generado</p>
        </div>
        """
        self.web_view.setHtml(html_placeholder)

    def verificar_mapa_inicial(self):
        html_path = os.path.abspath("Mapa/MapaFinal.html")
        if os.path.exists(html_path):
            self.web_view.load(QUrl.fromLocalFile(html_path))

    def importar_recorrido(self):
        archivos, _ = QFileDialog.getOpenFileNames(self, "Selecciona video y coordenadas", "")
        if len(archivos) != 2:
            QMessageBox.warning(self, "Error", "Debes seleccionar un video (.webm) y un archivo de coordenadas (.txt).")
            return

        video = next((f for f in archivos if f.lower().endswith(".webm")), None)
        coords = next((f for f in archivos if f.lower().endswith(".txt")), None)
        if not video or not coords:
            QMessageBox.warning(self, "Error", "Selecciona un video (.webm) y un archivo de coordenadas (.txt).")
            return

        base_dir_coords = os.path.abspath("Coords")
        base_dir_vids = os.path.abspath("Vids")
        n = 1
        while os.path.exists(os.path.join(base_dir_coords, f"recorrido{n}")):
            n += 1
        subfolder = f"recorrido{n}"

        coords_dest = os.path.join(base_dir_coords, subfolder)
        vids_dest = os.path.join(base_dir_vids, subfolder)
        os.makedirs(coords_dest, exist_ok=True)
        os.makedirs(vids_dest, exist_ok=True)

        shutil.copy(coords, os.path.join(coords_dest, "cordenadas.txt"))
        shutil.copy(video, os.path.join(vids_dest, "video.webm"))

        generar_mapa_desde_todas_las_subcarpetas()
        self.verificar_mapa_inicial()
        QMessageBox.information(self, "Importación exitosa", f"Recorrido importado en {subfolder}.")

    def extraer_frames_recorrido(self):
        # Selecciona el recorrido (subcarpeta) para extraer frames
        base_dir_vids = os.path.abspath("Vids")
        base_dir_imgs = os.path.abspath("Img")
        base_dir_coords = os.path.abspath("Coords")
        recorridos = [d for d in os.listdir(base_dir_vids) if os.path.isdir(os.path.join(base_dir_vids, d))]
        if not recorridos:
            QMessageBox.warning(self, "Error", "No hay recorridos para extraer frames.")
            return

        # Selecciona el último recorrido agregado
        recorrido = sorted(recorridos, key=lambda x: int(x.replace("recorrido", "")))[-1]
        video_path = os.path.join(base_dir_vids, recorrido, "video.webm")
        coords_path = os.path.join(base_dir_coords, recorrido, "cordenadas.txt")
        if not os.path.exists(video_path) or not os.path.exists(coords_path):
            QMessageBox.warning(self, "Error", "No se encontró el video o las coordenadas para el recorrido seleccionado.")
            return

        # Leer segundos desde el archivo de coordenadas
        segundos = []
        with open(coords_path, "r") as f:
            for linea in f:
                if "Segundo" in linea:
                    partes = linea.strip().split(":")
                    segundo = int(partes[0].replace("Segundo", "").strip())
                    segundos.append(segundo)

        if not segundos:
            QMessageBox.warning(self, "Error", "No se encontraron segundos en el archivo de coordenadas.")
            return

        img_dest = os.path.join(base_dir_imgs, recorrido)
        os.makedirs(img_dest, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duracion = int(total_frames / fps)

        for segundo in segundos:
            frame_id = int(segundo * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = cap.read()
            if ret:
                img_path = os.path.join(img_dest, f"{segundo}.webp")
                cv2.imwrite(img_path, frame)
        cap.release()

        # Validar que todos los frames existen
        faltantes = [s for s in segundos if not os.path.exists(os.path.join(img_dest, f"{s}.webp"))]
        if faltantes:
            QMessageBox.warning(self, "Error", f"Faltan algunos frames: {faltantes}")
        else:
            # Actualizar el mapa
            generar_mapa_desde_todas_las_subcarpetas()
            self.verificar_mapa_inicial()
            QMessageBox.information(self, "Frames extraídos", f"Frames extraídos y mapa actualizado para Img/{recorrido}")

    def on_cargar_click(self):
        html_path = os.path.abspath("Mapa/MapaFinal.html")
        if os.path.exists(html_path):
            self.web_view.load(QUrl.fromLocalFile(html_path))
        else:
            QMessageBox.critical(self, "Error", "❌ No se encontró el archivo")

    def borrar_datos(self):
        confirm = QMessageBox.question(self, "Confirmar eliminación",
            "¿Seguro que deseas borrar coordenadas, mapas, imágenes y videos?",
            QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            rutas = [
                os.path.abspath("Mapa/MapaFinal.html"),
                os.path.abspath("Mapa/MapaFinal.html.json"),
                os.path.abspath("Velocidad/velocidades.json"),
                os.path.abspath("Mapa"),
                os.path.abspath("Img"),
                os.path.abspath("Vids"),
                os.path.abspath("Coords"),
                os.path.abspath("Labels"),
                os.path.abspath(ESTADO_JSON),
            ]

            for ruta in rutas:
                if os.path.isfile(ruta):
                    os.remove(ruta)
                elif os.path.isdir(ruta):
                    shutil.rmtree(ruta)

            os.makedirs("Mapa", exist_ok=True)
            os.makedirs("Img", exist_ok=True)
            os.makedirs("Vids", exist_ok=True)
            os.makedirs("Coords", exist_ok=True)
            os.makedirs("Labels", exist_ok=True)

            self.estado = {
                "imagenes_cargadas": False,
                "imagen_segundos": [],
                "imagenes_cargadas_labels": False,
                "esperando_coords": False
            }
            self.guardar_estado()

            self.mostrar_placeholder_mapa()
            QMessageBox.information(self, "Eliminación completada", "🧹 Todo ha sido borrado correctamente.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MapaApp()
    ventana.show()
    sys.exit(app.exec_())

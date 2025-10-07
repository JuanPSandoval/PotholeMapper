import sys
import os
import shutil
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton,
    QFileDialog, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon
from PIL import Image, ImageDraw, ImageFont
from Map_generator import generar_mapa

file_path = None
imagen_segundos = []
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
        btn.clicked.connect(lambda: self.validar_boton(callback, tooltip))
        return btn

    def validar_boton(self, callback, tooltip):
        if callback == self.abrir_archivo and (not self.estado["imagenes_cargadas"] or not self.estado["esperando_coords"]):
            QMessageBox.information(self, "Instrucción", f"⚠️ '{tooltip}' requiere imágenes nuevas antes de cargar coordenadas.")
            return
        if callback == self.importar_labels and not self.estado["imagenes_cargadas"]:
            QMessageBox.information(self, "Instrucción", f"⚠️ '{tooltip}' requiere que primero se importen imágenes.")
            return
        if callback == self.importar_imagenes and self.estado["esperando_coords"]:
            QMessageBox.information(self, "Instrucción", "⚠️ Debes importar las coordenadas antes de subir un nuevo grupo de imágenes.")
            return
        callback()

    def crear_barra_navegacion(self):
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(8, 4, 8, 4)
        nav_bar.setSpacing(4)

        btn_cargar = self.crear_boton_icono("assets/icons/map.svg", "Cargar mapa", self.on_cargar_click)
        self.btn_archivo = self.crear_boton_icono("assets/icons/file.svg", "Seleccionar Coordenadas", self.abrir_archivo)
        btn_imagenes = self.crear_boton_icono("assets/icons/image.svg", "Importar imágenes", self.importar_imagenes)
        btn_videos = self.crear_boton_icono("assets/icons/video.svg", "Importar videos", self.importar_videos)
        self.btn_labels = self.crear_boton_icono("assets/icons/archive.svg", "Importar labels", self.importar_labels)
        btn_borrar = self.crear_boton_icono("assets/icons/trash.svg", "Borrar todo", self.borrar_datos)

        for btn in [btn_cargar, self.btn_archivo, btn_imagenes, btn_videos, self.btn_labels, btn_borrar]:
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
            <p style='font-size:14px;'>Importa coordenadas para visualizar el mapa generado</p>
        </div>
        """
        self.web_view.setHtml(html_placeholder)

    def verificar_mapa_inicial(self):
        html_path = os.path.abspath("Mapa/MapaFinal.html")
        if os.path.exists(html_path):
            self.web_view.load(QUrl.fromLocalFile(html_path))

    def abrir_archivo(self):
        global file_path
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Archivos de texto (*.txt)")
        if path:
            file_path = path
            print("Archivo seleccionado:", file_path)
            generar_mapa(file_path, self.estado["imagen_segundos"])
            QMessageBox.information(self, "Importación exitosa", "✅ Se importaron correctamente las coordenadas.")
            self.estado["esperando_coords"] = False
            self.guardar_estado()

    def on_cargar_click(self):
        html_path = os.path.abspath("Mapa/MapaFinal.html")
        if os.path.exists(html_path):
            self.web_view.load(QUrl.fromLocalFile(html_path))
        else:
            QMessageBox.critical(self, "Error", "❌ No se encontró el archivo")

    def importar_imagenes(self):
        global imagen_segundos
        imagen_segundos = []

        folder_destino = os.path.abspath("Img")
        os.makedirs(folder_destino, exist_ok=True)

        archivos, _ = QFileDialog.getOpenFileNames(self, "Seleccionar imágenes", "", "Imágenes WEBP (*.webp)")
        if not archivos:
            return

        segundos_originales = []
        for archivo in archivos:
            base = os.path.splitext(os.path.basename(archivo))[0]
            if base.isdigit():
                segundos_originales.append(int(base))
        imagen_segundos = segundos_originales.copy()

        existentes = [int(os.path.splitext(f)[0]) for f in os.listdir(folder_destino)
                      if f.lower().endswith(".webp") and os.path.splitext(f)[0].isdigit()]
        max_existente = max(existentes, default=0)

        for i, archivo in enumerate(archivos):
            nuevo_nombre = f"{max_existente + i + 1}.webp"
            nueva_ruta = os.path.join(folder_destino, nuevo_nombre)
            shutil.copy(archivo, nueva_ruta)

        self.estado["imagenes_cargadas"] = True
        self.estado["imagen_segundos"] = imagen_segundos
        self.estado["esperando_coords"] = True
        self.guardar_estado()

        QMessageBox.information(self, "Importación exitosa", f"✅ Se importaron {len(archivos)} imágenes.")
        print("Segundos originales:", imagen_segundos)

    def importar_videos(self):
        folder_destino = os.path.abspath("Vids")
        os.makedirs(folder_destino, exist_ok=True)

        archivos, _ = QFileDialog.getOpenFileNames(self, "Seleccionar videos", "", "Videos WEBM (*.webm)")
        if archivos:
            existentes = [int(os.path.splitext(f)[0]) for f in os.listdir(folder_destino)
                          if f.endswith(".webm") and os.path.splitext(f)[0].isdigit()]
            max_num = max(existentes, default=0) + 1

            for i, archivo in enumerate(archivos):
                nuevo_nombre = f"{max_num + i}.webm"
                nueva_ruta = os.path.join(folder_destino, nuevo_nombre)
                shutil.copy(archivo, nueva_ruta)

            QMessageBox.information(self, "Importación exitosa", f"✅ Se importaron {len(archivos)} videos.")

    def importar_labels(self):
        if not self.estado["imagenes_cargadas"]:
            QMessageBox.warning(self, "Validación", "⚠️ Primero debes importar imágenes antes de cargar labels.")
            return

        folder_labels = os.path.abspath("Labels")
        folder_imgs = os.path.abspath("Img")
        os.makedirs(folder_labels, exist_ok=True)

        archivos, _ = QFileDialog.getOpenFileNames(self, "Seleccionar labels", "", "Archivos de texto (*.txt)")
        if not archivos:
            QMessageBox.warning(self, "Sin archivos", "⚠️ No se seleccionaron archivos de labels.")
            return

        existentes = [int(os.path.splitext(f)[0]) for f in os.listdir(folder_labels)
                      if f.endswith(".txt") and os.path.splitext(f)[0].isdigit()]
        max_num = max(existentes, default=0) + 1

        actualizados = 0

        for i, archivo in enumerate(archivos):
            nuevo_nombre = f"{max_num + i}.txt"
            ruta_label_destino = os.path.join(folder_labels, nuevo_nombre)
            shutil.copy(archivo, ruta_label_destino)

            nombre_base = os.path.splitext(nuevo_nombre)[0]
            img_path = os.path.join(folder_imgs, f"{nombre_base}.webp")
            if not os.path.exists(img_path):
                continue

            try:
                with open(ruta_label_destino, "r") as f:
                    lines = f.readlines()

                img = Image.open(img_path).convert("RGB")
                draw = ImageDraw.Draw(img)
                w, h = img.size
                font = ImageFont.load_default()

                for line in lines:
                    parts = list(map(float, line.strip().split()))
                    if len(parts) == 4:
                        x, y, ancho, alto = parts
                    elif len(parts) == 5:
                        _, x, y, ancho, alto = parts
                    else:
                        continue

                    x0 = (x - ancho / 2) * w
                    y0 = (y - alto / 2) * h
                    x1 = (x + ancho / 2) * w
                    y1 = (y + alto / 2) * h
                    draw.rectangle([x0, y0, x1, y1], outline="blue", width=3)

                    text = "pothole"
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x, text_y = x0, y0 - text_height - 4

                    draw.rectangle([text_x, text_y, text_x + text_width + 4, text_y + text_height + 4], fill="blue")
                    draw.text((text_x + 2, text_y + 2), text, fill="white", font=font)

                img.save(img_path)
                actualizados += 1

            except Exception as e:
                print(f"⚠️ Error procesando {nuevo_nombre}: {e}")

        if actualizados > 0:
            QMessageBox.information(self, "Proceso completado", f"✅ Se actualizaron {actualizados} imágenes.")
            self.estado["imagenes_cargadas_labels"] = True
            self.guardar_estado()
        else:
            QMessageBox.warning(self, "Sin cambios", "⚠️ No se actualizó ninguna imagen.")

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

import sys
import os
import shutil
import json
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton,
    QFileDialog, QHBoxLayout, QMessageBox, QLabel, QPushButton,
    QScrollArea, QGridLayout, QSizePolicy, QDialog, QSpacerItem
)
from PyQt5.QtCore import Qt, QUrl, QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QMovie
from Map_generator import generar_mapa_desde_todas_las_subcarpetas

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        # Fondo completamente transparente
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
        """)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.label_gif = QLabel()
        self.label_gif.setAlignment(Qt.AlignCenter)
        movie = QMovie("assets/icons/loading.gif")
        if not movie.isValid():
            self.label_gif.setText("⏳")
            self.label_gif.setStyleSheet("font-size: 60px; color: #00aaff; background: transparent;")
        else:
            self.label_gif.setMovie(movie)
            movie.start()
        layout.addWidget(self.label_gif)

        label_text = QLabel("Extrayendo frames, por favor espera...")
        label_text.setAlignment(Qt.AlignCenter)
        label_text.setStyleSheet("color: #09164f; font-size: 18px; margin-top: 10px; background: transparent;")
        layout.addWidget(label_text)

        self.setFixedSize(320, 220)

class ZoomImageWindow(QWidget):
    def __init__(self, img_path):
        super().__init__()
        self.setWindowTitle("Vista ampliada")
        layout = QVBoxLayout()
        self.setLayout(layout)
        pixmap = QPixmap(img_path)
        lbl = QLabel()
        lbl.setPixmap(pixmap.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        self.setMinimumSize(400, 300)

class FrameExtractorThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, video_path, segundos, img_dest):
        super().__init__()
        self.video_path = video_path
        self.segundos = segundos
        self.img_dest = img_dest

    def run(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total = len(self.segundos)
            for idx, segundo in enumerate(self.segundos):
                frame_id = int(segundo * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                ret, frame = cap.read()
                if ret:
                    img_path = os.path.join(self.img_dest, f"{segundo}.webp")
                    cv2.imwrite(img_path, frame)
                self.progress.emit(idx + 1, total)
            cap.release()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class FrameReviewWindow(QWidget):
    def __init__(self, img_folder, on_finish_callback):
        super().__init__()
        self.setWindowTitle("Revisión de Frames")
        self.img_folder = img_folder
        self.on_finish_callback = on_finish_callback
        self.selected = set()
        self.img_labels = []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: #23272e;
            }
            QLabel {
                color: #fff;
            }
            QPushButton {
                background: #0078d7;
                color: #fff;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 15px;
            }
            QPushButton:hover {
                background: #005fa3;
            }
        """)
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Selecciona imágenes para borrar (Ctrl+Click). Doble click para ampliar.")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; margin: 10px 0 18px 0; color: #fff;")
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.frame_widget = QWidget()
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        self.frame_widget.setLayout(self.grid)
        self.scroll.setWidget(self.frame_widget)
        layout.addWidget(self.scroll)

        btns_layout = QHBoxLayout()
        btn_borrar = QPushButton("Borrar seleccionadas")
        btn_borrar.clicked.connect(self.borrar_seleccionadas)
        btn_enviar = QPushButton("Enviar / Seguir")
        btn_enviar.clicked.connect(self.finish_and_close)
        btns_layout.addStretch()
        btns_layout.addWidget(btn_borrar)
        btns_layout.addWidget(btn_enviar)
        btns_layout.addStretch()
        layout.addLayout(btns_layout)

        self.load_images()

    def load_images(self):
        # Limpiar grid
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        self.img_labels = []
        self.selected = set()

        images = sorted([f for f in os.listdir(self.img_folder) if f.lower().endswith(".webp")])
        for idx, img_name in enumerate(images):
            img_path = os.path.join(self.img_folder, img_name)
            pixmap = QPixmap(img_path).scaled(380, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl = QLabel()
            lbl.setPixmap(pixmap)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setToolTip(img_name)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            lbl.setStyleSheet("""
                border: 2px solid transparent;
                margin: 2px;
                background: #181a20;
                border-radius: 10px;
            """)
            lbl.setCursor(QCursor(Qt.PointingHandCursor))
            lbl.mousePressEvent = lambda e, l=lbl, p=img_path, i=idx: self.toggle_select(e, l, p, i)
            lbl.mouseDoubleClickEvent = lambda e, p=img_path: self.zoom_image(p)
            self.grid.addWidget(lbl, idx // 5, idx % 5)
            self.img_labels.append((lbl, img_path))

    def toggle_select(self, event, label, img_path, idx):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # Multi-selección con Ctrl
            if img_path in self.selected:
                self.selected.remove(img_path)
                label.setStyleSheet("""
                    border: 2px solid transparent;
                    margin: 2px;
                    background: #181a20;
                    border-radius: 10px;
                """)
            else:
                self.selected.add(img_path)
                label.setStyleSheet("""
                    border: 2.5px solid #00aaff;
                    margin: 2px;
                    background: #181a20;
                    border-radius: 10px;
                """)
        else:
            # Selección simple
            for lbl, path in self.img_labels:
                lbl.setStyleSheet("""
                    border: 2px solid transparent;
                    margin: 2px;
                    background: #181a20;
                    border-radius: 10px;
                """)
            self.selected = {img_path}
            label.setStyleSheet("""
                border: 2.5px solid #00aaff;
                margin: 2px;
                background: #181a20;
                border-radius: 10px;
            """)

    def borrar_seleccionadas(self):
        if not self.selected:
            QMessageBox.information(self, "Nada seleccionado", "Selecciona imágenes con Ctrl+Click para borrar.")
            return
        for img_path in list(self.selected):
            try:
                os.remove(img_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo borrar la imagen: {e}")
        self.load_images()

    def zoom_image(self, img_path):
        self.zoom_win = ZoomImageWindow(img_path)
        self.zoom_win.show()

    def finish_and_close(self):
        self.on_finish_callback()
        self.close()

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

        self.crear_barra_navegacion()
        self.crear_vista_mapa()
        self.verificar_mapa_inicial()

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
        base_dir_vids = os.path.abspath("Vids")
        base_dir_imgs = os.path.abspath("Img")
        base_dir_coords = os.path.abspath("Coords")
        recorridos = [d for d in os.listdir(base_dir_vids) if os.path.isdir(os.path.join(base_dir_vids, d))]
        if not recorridos:
            QMessageBox.warning(self, "Error", "No hay recorridos para extraer frames.")
            return

        recorrido = sorted(recorridos, key=lambda x: int(x.replace("recorrido", "")))[-1]
        video_path = os.path.join(base_dir_vids, recorrido, "video.webm")
        coords_path = os.path.join(base_dir_coords, recorrido, "cordenadas.txt")
        if not os.path.exists(video_path) or not os.path.exists(coords_path):
            QMessageBox.warning(self, "Error", "No se encontró el video o las coordenadas para el recorrido seleccionado.")
            return

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

        # Pantalla de carga personalizada
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()
        QApplication.processEvents()

        def on_progress(val, total):
            # No barra, solo mantener el loading visible
            pass

        def on_finished():
            self.loading_dialog.close()
            faltantes = [s for s in segundos if not os.path.exists(os.path.join(img_dest, f"{s}.webp"))]
            if faltantes:
                QMessageBox.warning(self, "Error", f"Faltan algunos frames: {faltantes}")
            else:
                self.revision_window = FrameReviewWindow(
                    img_dest,
                    on_finish_callback=self.actualizar_mapa_despues_revision
                )
                self.revision_window.show()

        def on_error(msg):
            self.loading_dialog.close()
            QMessageBox.critical(self, "Error", f"Error extrayendo frames: {msg}")

        self.extractor_thread = FrameExtractorThread(video_path, segundos, img_dest)
        self.extractor_thread.progress.connect(on_progress)
        self.extractor_thread.finished.connect(on_finished)
        self.extractor_thread.error.connect(on_error)
        self.extractor_thread.start()

    def actualizar_mapa_despues_revision(self):
        generar_mapa_desde_todas_las_subcarpetas()
        self.verificar_mapa_inicial()
        QMessageBox.information(self, "Frames procesados", "Frames revisados y mapa actualizado.")

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

            self.mostrar_placeholder_mapa()
            QMessageBox.information(self, "Eliminación completada", "🧹 Todo ha sido borrado correctamente.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MapaApp()
    ventana.show()
    sys.exit(app.exec_())

import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton,
    QFileDialog, QHBoxLayout, QMessageBox, QLabel, QPushButton,
    QScrollArea, QGridLayout, QSizePolicy, QDialog, QProgressBar
)
from PyQt5.QtCore import Qt, QUrl, QSize, QThread, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap, QCursor
from Map_generator import generar_mapa_desde_todas_las_subcarpetas

from frame_selector import load_hyperiqa_model, flujo_completo

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
            QLabel {
                color: #09164f;
                font-size: 18px;
                background: transparent;
            }
            QProgressBar {
                border: 2px solid #0078d7;
                border-radius: 8px;
                text-align: center;
                font-size: 16px;
                color: #fff;
                background: #23272e;
                height: 28px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00aaff, stop:1 #0078d7
                );
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.label = QLabel("Extrayendo frames, por favor espera...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(32)
        layout.addWidget(self.progress)

        self.setFixedSize(400, 160)

    def set_progress(self, value, total):
        percent = int((value / total) * 100) if total > 0 else 0
        self.progress.setValue(percent)
        self.label.setText(f"Extrayendo frames ({value}/{total})...")

class FrameProcessingThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, video_path, clips_dir, frameclips_dir, framerep_dest, duracion_clip, model_hyper, transforms, device):
        super().__init__()
        self.video_path = video_path
        self.clips_dir = clips_dir
        self.frameclips_dir = frameclips_dir
        self.framerep_dest = framerep_dest
        self.duracion_clip = duracion_clip
        self.model_hyper = model_hyper
        self.transforms = transforms
        self.device = device

    def run(self):
        try:
            def progress_callback(val, total):
                self.progress.emit(val, total)
            flujo_completo(
                video_path=self.video_path,
                clips_dir=self.clips_dir,
                frameclips_dir=self.frameclips_dir,
                framerep_dest=self.framerep_dest,
                duracion_clip=self.duracion_clip,
                model_hyper=self.model_hyper,
                transforms=self.transforms,
                device=self.device,
                progress_callback=progress_callback
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
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

class FrameReviewWindow(QWidget):
    def __init__(self, img_folder, img_dest, on_finish_callback):
        super().__init__()
        self.setWindowTitle("Revisión de Frames")
        self.img_folder = img_folder
        self.img_dest = img_dest
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
        # Al pulsar "Enviar / Seguir", copiar los frames restantes a Img/recorridoX/
        if os.path.exists(self.img_dest):
            for f in os.listdir(self.img_dest):
                os.remove(os.path.join(self.img_dest, f))
        else:
            os.makedirs(self.img_dest, exist_ok=True)
        for f in os.listdir(self.img_folder):
            if f.lower().endswith(".webp"):
                shutil.copy(os.path.join(self.img_folder, f), os.path.join(self.img_dest, f))
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
        base_dir_coords = os.path.abspath("Coords")
        base_dir_clips = os.path.abspath("Clips")
        base_dir_frameclips = os.path.abspath("FrameClips")
        base_dir_framerep = os.path.abspath("frameRep")
        base_dir_imgs = os.path.abspath("Img")
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
        clips_dir = os.path.join(base_dir_clips, recorrido)
        frameclips_dir = os.path.join(base_dir_frameclips, recorrido)
        framerep_dest = os.path.join(base_dir_framerep, recorrido)
        img_dest = os.path.join(base_dir_imgs, recorrido)
        os.makedirs(clips_dir, exist_ok=True)
        os.makedirs(frameclips_dir, exist_ok=True)
        os.makedirs(framerep_dest, exist_ok=True)
        os.makedirs(img_dest, exist_ok=True)

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.show()
        QApplication.processEvents()

        try:
            model_hyper, transforms, device = load_hyperiqa_model('./pretrained/koniq_pretrained.pkl')
            self.thread = FrameProcessingThread(
                video_path=video_path,
                clips_dir=clips_dir,
                frameclips_dir=frameclips_dir,
                framerep_dest=framerep_dest,
                duracion_clip=2,
                model_hyper=model_hyper,
                transforms=transforms,
                device=device
            )
            self.thread.finished.connect(self.on_frames_processed)
            self.thread.error.connect(self.on_frames_error)
            self.thread.progress.connect(self.on_progress_update)
            self.thread.start()
        except Exception as e:
            self.progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Error extrayendo frames: {e}")

    def on_progress_update(self, value, total):
        self.progress_dialog.set_progress(value, total)

    def on_frames_processed(self):
        self.progress_dialog.close()
        recorrido = self.get_last_recorrido()
        framerep_dest = os.path.join(os.path.abspath("frameRep"), recorrido)
        img_dest = os.path.join(os.path.abspath("Img"), recorrido)
        self.revision_window = FrameReviewWindow(
            img_folder=framerep_dest,
            img_dest=img_dest,
            on_finish_callback=self.actualizar_mapa_despues_revision
        )
        self.revision_window.show()

    def on_frames_error(self, msg):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Error", f"Error extrayendo frames: {msg}")

    def get_last_recorrido(self):
        base_dir_vids = os.path.abspath("Vids")
        recorridos = [d for d in os.listdir(base_dir_vids) if os.path.isdir(os.path.join(base_dir_vids, d))]
        if not recorridos:
            return ""
        return sorted(recorridos, key=lambda x: int(x.replace("recorrido", "")))[-1]

    def actualizar_mapa_despues_revision(self):
        generar_mapa_desde_todas_las_subcarpetas()
        html_path = os.path.abspath("Mapa/MapaFinal.html")
        url = QUrl.fromLocalFile(html_path)
        url.setQuery(f"v={os.path.getmtime(html_path)}")
        self.web_view.load(url)
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
                os.path.abspath("Clips"),
                os.path.abspath("frameclips"),
                os.path.abspath("frameRep")
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
            os.makedirs("Clips", exist_ok=True)
            os.makedirs("frameclips", exist_ok=True)
            os.makedirs("frameRep", exist_ok=True)

            self.mostrar_placeholder_mapa()
            QMessageBox.information(self, "Eliminación completada", "🧹 Todo ha sido borrado correctamente.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MapaApp()
    ventana.show()
    sys.exit(app.exec_())

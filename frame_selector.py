
# frame_selector.py
import os
import cv2
import torch
import torchvision
import numpy as np
from PIL import Image
from skimage.measure import shannon_entropy
import models

# =========================================================
# --- CONFIGURACIÓN DE MODELO Y TRANSFORMACIONES ---
# =========================================================
def load_hyperiqa_model(model_path='./pretrained/koniq_pretrained.pkl', device=None):
    """Carga el modelo HyperIQA preentrenado."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model_hyper = models.HyperNet(16, 112, 224, 112, 56, 28, 14, 7)
    model_hyper.load_state_dict(torch.load(model_path, map_location=device))
    model_hyper.to(device)
    model_hyper.eval()

    transforms = torchvision.transforms.Compose([
        torchvision.transforms.Resize((512, 384)),
        torchvision.transforms.CenterCrop(size=224),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize(mean=(0.485, 0.456, 0.406),
                                         std=(0.229, 0.224, 0.225))
    ])
    return model_hyper, transforms, device

# =========================================================
# --- FUNCIONES AUXILIARES ---
# =========================================================
def pil_loader_from_frame(frame):
    """Convierte un frame OpenCV (BGR) en una imagen PIL (RGB)."""
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

def calcular_nitidez(gray):
    """Calcula la nitidez de una imagen usando el operador Laplaciano."""
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def calcular_contraste(gray):
    """Calcula el contraste RMS de una imagen en escala de grises."""
    return np.sqrt(np.mean((gray - np.mean(gray)) ** 2))

def calcular_entropia(gray):
    """Calcula la entropía de Shannon de una imagen en escala de grises."""
    return shannon_entropy(gray)

def evaluar_hyperiqa(frame, model_hyper, transforms, device):
    """Evalúa la calidad de un frame con HyperIQA (dos recortes aleatorios)."""
    pred_scores = []
    for _ in range(2):  # Mayor robustez
        img = pil_loader_from_frame(frame)
        img = transforms(img).unsqueeze(0).to(device)
        with torch.no_grad():
            paras = model_hyper(img)
            model_target = models.TargetNet(paras)
            for param in model_target.parameters():
                param.requires_grad = False
            pred = model_target(paras['target_in_vec'])
        pred_scores.append(float(pred.item()))
    return np.mean(pred_scores)

def dividir_video_en_clips(video_path, clips_dir, duracion_clip=2):
    """Divide un video en clips de duración específica (usa .avi y XVID para máxima compatibilidad)."""
    os.makedirs(clips_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"No se pudo abrir el video: {video_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_por_clip = duracion_clip * fps
    clip_idx = 1
    frame_idx = 0
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # AVI/XVID es universal

    while frame_idx < total_frames:
        clip_path = os.path.join(clips_dir, f"clip{clip_idx}.avi")
        out = None
        frames_this_clip = 0
        while frames_this_clip < frames_por_clip and frame_idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if out is None:
                h, w = frame.shape[:2]
                out = cv2.VideoWriter(clip_path, fourcc, fps, (w, h))
            out.write(frame)
            frames_this_clip += 1
            frame_idx += 1
        if out is not None:
            out.release()
        clip_idx += 1

    cap.release()

def extraer_frames_de_clips(clips_dir, frameclips_dir):
    """Extrae frames de los clips de video y los guarda como imágenes."""
    os.makedirs(frameclips_dir, exist_ok=True)
    for clip_file in sorted(os.listdir(clips_dir)):
        if not (clip_file.endswith('.avi') or clip_file.endswith('.mp4')):
            continue
        clip_path = os.path.join(clips_dir, clip_file)
        clip_name = os.path.splitext(clip_file)[0]
        out_dir = os.path.join(frameclips_dir, clip_name)
        os.makedirs(out_dir, exist_ok=True)
        cap = cv2.VideoCapture(clip_path)
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_path = os.path.join(out_dir, f"frame{idx:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            idx += 1
        cap.release()

def seleccionar_mejor_frame_por_clip(frameclips_dir, framerep_dest, model_hyper, transforms, device, progress_callback=None):
    """Selecciona el mejor frame de cada clip basado en la calidad estimada."""
    os.makedirs(framerep_dest, exist_ok=True)
    clip_folders = [f for f in sorted(os.listdir(frameclips_dir)) if os.path.isdir(os.path.join(frameclips_dir, f))]
    total_clips = len(clip_folders)
    for idx, clip_folder in enumerate(clip_folders, 1):
        clip_path = os.path.join(frameclips_dir, clip_folder)
        best_score = -float('inf')
        best_frame_path = None
        for frame_file in sorted(os.listdir(clip_path)):
            if not frame_file.endswith('.jpg'):
                continue
            frame_path = os.path.join(clip_path, frame_file)
            frame = cv2.imread(frame_path)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            nitidez = calcular_nitidez(gray)
            contraste = calcular_contraste(gray)
            entropia = calcular_entropia(gray)
            hyperiqa = evaluar_hyperiqa(frame, model_hyper, transforms, device)
            score = 0.3 * nitidez + 0.2 * contraste + 0.2 * entropia + 0.3 * hyperiqa
            if score > best_score:
                best_score = score
                best_frame_path = frame_path
        if best_frame_path:
            out_name = f"{idx}.webp"  # SOLO el número del clip
            out_path = os.path.join(framerep_dest, out_name)
            frame = cv2.imread(best_frame_path)
            cv2.imwrite(out_path, frame)
        if progress_callback:
            progress_callback(idx, total_clips)

def flujo_completo(video_path, clips_dir, frameclips_dir, framerep_dest, duracion_clip, model_hyper, transforms, device, progress_callback=None):
    """Ejecuta el flujo completo: dividir video, extraer frames y seleccionar mejor frame por clip."""
    dividir_video_en_clips(video_path, clips_dir, duracion_clip=duracion_clip)
    extraer_frames_de_clips(clips_dir, frameclips_dir)
    seleccionar_mejor_frame_por_clip(frameclips_dir, framerep_dest, model_hyper, transforms, device, progress_callback=progress_callback)

# =========================================================
# --- MAIN PARA EJECUCIÓN DIRECTA ---
# =========================================================
if __name__ == "__main__":
    # --- Configuración de entrada/salida ---
    video_path = ""
    output_dir = ""

    # --- Cargar modelo y transformaciones ---
    model_hyper, transforms, device = load_hyperiqa_model('./pretrained/koniq_pretrained.pkl')

    # --- Procesar video ---
    procesar_video(video_path, output_dir, frames_per_clip=60,
                   model_hyper=model_hyper, transforms=transforms, device=device)

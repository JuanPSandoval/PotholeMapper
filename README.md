# 🕳️ Pothole Detection V2 — Smart Road Analysis System  

Pothole Detection V2 is an AI-powered system designed to detect and geolocate potholes using a combination of mobile data collection, GPS tracking, and video processing.  
The goal of this project is to enhance road maintenance processes and contribute to smarter, safer cities.

---

## 🚀 Features

- 📍 **Precise Geolocation**: Captures GPS coordinates every second while recording videos.  
- 🎥 **Video Integration**: Each road segment corresponds to a specific video file.  
- 🗺️ **Interactive Map**: Displays grouped coordinates and allows video playback when clicking on a route.  
- 📊 **Data Export**: Automatically generates JSON and Excel files for later analysis.  
- 🌍 **Offline Support**: The app works without constant internet access and syncs data later.  

---

## 🧩 Tech Stack

- **Python 3.13**  
- **PyQt5** — for desktop UI  
- **PyQtWebEngine** — for embedded map visualization  
- **Folium** — for generating interactive HTML maps  
- **OpenCV** — for video capture and processing  
- **Pandas / OpenPyXL** — for data analysis and export  
- **JSON** — for structured coordinate and video grouping  

---

## 📂 Project Structure

```
My_app/
│
├── main.py                   # Main application launcher
├── requirements.txt          # Dependencies
├── generacionMapas/          # Map generation scripts
├── Labels/                   # Labels for road sections
├── Mapa/                     # Folder containing final HTML map
├── Vids/                     # Video recordings
└── velocidad/                # JSON files with average speed per group
```

---

## ⚙️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/JuanPSandoval/PotholeMapper.git
   cd Pothole-Detection-V2/My_app
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # (on Windows)
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

---

## 💡 How It Works

1. The system records a video while collecting GPS data in real-time.  
2. Each group of coordinates is linked to a specific video.  
3. The map is generated with clickable paths — clicking a line opens the related video.  
4. Hovering over a line shows the **average speed** of that segment.  

---

## 🧠 Project Vision

This project aims to empower **data-driven road maintenance** by making it easier for local governments and communities to identify and address infrastructure issues efficiently.  
Future improvements include:
- Integration with cloud databases  
- Real-time detection using AI inference models  
- Enhanced data dashboards  

---

## 👨‍💻 Author

**Juan Sandoval**  
📍 Colombia  
💼 BackEnd Developer

---

⭐ *If you find this project useful, consider giving it a star on GitHub!* ⭐

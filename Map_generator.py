import folium
import os
import json
from geopy.distance import geodesic

HTML_MAP_PATH = "Mapa/MapaFinal.html"
VELOCIDAD_PATH = "Velocidad/velocidades.json"

def txt_a_json(txt_path, json_path):
    """
    Convierte un archivo .txt de coordenadas a un archivo .json con el formato {"grupos": [[lat, lon], ...]}
    """
    puntos = []
    segundos = []
    with open(txt_path, "r") as archivo:
        for linea in archivo:
            if "Segundo" in linea:
                partes = linea.strip().split(":")
                segundo = int(partes[0].replace("Segundo", "").strip())
                coords = partes[1].split(",")
                lat = float(coords[0].split("=")[1].strip())
                lon = float(coords[1].split("=")[1].strip())
                puntos.append([lat, lon])
                segundos.append(segundo)
    if puntos:
        with open(json_path, "w") as f:
            json.dump({"grupos": [puntos], "segundos": segundos}, f, indent=4)

def calcular_velocidades(grupos, segundos_data):
    velocidades = []
    for i, grupo in enumerate(grupos):
        if len(grupo) < 2 or i >= len(segundos_data):
            velocidades.append(0)
            continue

        segundos = segundos_data[i]
        total_dist = 0
        total_tiempo_h = 0

        for j in range(len(grupo) - 1):
            lat1, lon1 = grupo[j][0], grupo[j][1]
            lat2, lon2 = grupo[j+1][0], grupo[j+1][1]
            tiempo_seg = segundos[j+1] - segundos[j]
            tiempo_h = tiempo_seg / 3600
            dist_km = geodesic((lat1, lon1), (lat2, lon2)).km
            if tiempo_h > 0:
                total_dist += dist_km
                total_tiempo_h += tiempo_h

        vel = total_dist / total_tiempo_h if total_tiempo_h > 0 else 0
        velocidades.append(round(vel, 2))

    return velocidades

def leer_todos_los_grupos():
    base_dir = "Coords"
    todos_los_grupos = []
    segundos_grupos = []
    nombres_recorridos = []
    for sub in os.listdir(base_dir):
        sub_path = os.path.join(base_dir, sub)
        if os.path.isdir(sub_path):
            json_file = os.path.join(sub_path, "cordenadas.json")
            txt_file = os.path.join(sub_path, "cordenadas.txt")
            # Si no existe el json pero sí el txt, conviértelo
            if not os.path.exists(json_file) and os.path.exists(txt_file):
                txt_a_json(txt_file, json_file)
            if os.path.exists(json_file):
                with open(json_file, "r") as f:
                    data = json.load(f)
                    grupos = data.get("grupos", [])
                    segundos = data.get("segundos", [])
                    if grupos:
                        todos_los_grupos.append(grupos[0])
                        segundos_grupos.append(segundos)
                        nombres_recorridos.append(sub)
    return todos_los_grupos, segundos_grupos, nombres_recorridos

def generar_mapa_desde_todas_las_subcarpetas():
    print("Generando mapa desde todas las subcarpetas...")
    todos_los_grupos, segundos_grupos, nombres_recorridos = leer_todos_los_grupos()
    if not todos_los_grupos:
        print("❌ No hay puntos registrados para generar el mapa.")
        return

    velocidades = calcular_velocidades(todos_los_grupos, segundos_grupos)

    mapa = folium.Map(location=todos_los_grupos[0][0], zoom_start=18, tiles="OpenStreetMap")
    total_idx = 1

    for i, (grupo, segundos, nombre_recorrido) in enumerate(zip(todos_los_grupos, segundos_grupos, nombres_recorridos)):
        coords_js = [[lat, lon] for lat, lon in grupo]
        video_src = f"../vids/{nombre_recorrido}/video.webm"

        js = f"""
        function onClickGrupo{i}() {{
            var modal = document.getElementById('videoModal');
            var video = document.getElementById('videoPlayer');
            video.src = '{video_src}';
            modal.style.display = 'flex';
        }}
        """
        mapa.get_root().script.add_child(folium.Element(js))

        polyline = folium.PolyLine(grupo, color="blue", weight=4, opacity=0.8)
        polyline.add_child(folium.Popup(f'<a href="#" onclick="onClickGrupo{i}()">Ver video</a>'))
        polyline.add_to(mapa)

        # Mapear solo los frames que existen en Img/recorridoX con nombre igual al segundo
        img_dir = os.path.join("Img", nombre_recorrido)
        for idx, (lat, lon) in enumerate(grupo):
            if idx < len(segundos):
                segundo = segundos[idx]
                img_path = os.path.join(img_dir, f"{segundo}.webp")
                if os.path.exists(img_path):
                    # Popup solo con la imagen y opción de ampliar
                    popup = folium.Popup(
                        f"""
                        <img src='../Img/{nombre_recorrido}/{segundo}.webp' width='200' style='cursor:pointer;' onclick="ampliarImagen('../Img/{nombre_recorrido}/{segundo}.webp')">
                        """,
                        max_width=220
                    )
                    folium.Marker(
                        location=[lat, lon],
                        icon=folium.Icon(color="blue", icon="camera", prefix="fa"),
                        popup=popup
                    ).add_to(mapa)
            total_idx += 1

    todos_los_puntos = [pt for grupo in todos_los_grupos for pt in grupo]
    mapa.fit_bounds(todos_los_puntos)

    # Modal de video
    modal_html = """
    <div id="videoModal" style="
        display: none;
        position: fixed;
        z-index: 10000;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.8);
        justify-content: center;
        align-items: center;
        flex-direction: column;
        ">

        <span onclick="cerrarModal()" style="
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            z-index: 10001;">&times;</span>

        <div style="
            width: 80%;
            max-width: 800px;
            background: transparent;
            border-radius: 10px;
            display: flex;
            justify-content: center;
            align-items: center;
        ">
            <video id="videoPlayer" style="
                width: 100%;
                height: auto;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            " controls autoplay allowfullscreen>
                <source src="" type="video/webm">
                Tu navegador no soporta la reproducción de video.
            </video>
        </div>
    </div>

    <div id="imgModal" style="
        display: none;
        position: fixed;
        z-index: 10001;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.85);
        justify-content: center;
        align-items: center;
        flex-direction: column;
    ">
        <span onclick="cerrarImgModal()" style="
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            z-index: 10002;">&times;</span>
        <img id="imgAmpliada" src="" style="
            max-width: 90vw;
            max-height: 90vh;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.7);
        ">
    </div>

    <script>
    function cerrarModal() {
        var modal = document.getElementById('videoModal');
        var video = document.getElementById('videoPlayer');
        video.pause();
        video.currentTime = 0;
        modal.style.display = 'none';
    }
    function ampliarImagen(src) {
        var modal = document.getElementById('imgModal');
        var img = document.getElementById('imgAmpliada');
        img.src = src;
        modal.style.display = 'flex';
    }
    function cerrarImgModal() {
        var modal = document.getElementById('imgModal');
        modal.style.display = 'none';
    }
    </script>
    """
    mapa.get_root().html.add_child(folium.Element(modal_html))

    # Script para mostrar coordenadas al pasar el mouse por encima
    hover_script = """
    <script>
    window.addEventListener("load", function () {
        var mapInstance = Object.values(window).find(v => v instanceof L.Map);
        if (!mapInstance) return;

        var coordDisplay = L.control({position: 'bottomleft'});
        coordDisplay.onAdd = function () {
            var div = L.DomUtil.create('div', 'coord-display');
            div.style.padding = '6px 10px';
            div.style.background = 'rgba(255, 255, 255, 0.9)';
            div.style.fontSize = '14px';
            div.style.fontFamily = 'monospace';
            div.style.borderRadius = '5px';
            div.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';
            div.innerHTML = '📍 Pon el mouse sobre una línea...';
            return div;
        };
        coordDisplay.addTo(mapInstance);
        var coordDiv = document.querySelector('.coord-display');

        function mostrarDatos(index, e) {
            coordDiv.innerHTML =
                "📍 Lat: " + e.latlng.lat.toFixed(6) +
                "<br>📍 Lng: " + e.latlng.lng.toFixed(6);
        }

        function limpiarCoords() {
            coordDiv.innerHTML = "📍 Hover sobre una línea...";
        }

        let lineIndex = 0;
        mapInstance.eachLayer(function(layer) {
            if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
                const idx = lineIndex;
                layer.on('mousemove', function(e) { mostrarDatos(idx, e); });
                layer.on('mouseout', limpiarCoords);
                lineIndex++;
            }
        });
    });
    </script>
    """
    mapa.get_root().html.add_child(folium.Element(hover_script))

    mapa.save(HTML_MAP_PATH)
    print(f"✅ Mapa guardado en: {HTML_MAP_PATH}")

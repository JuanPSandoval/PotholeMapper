import folium
import os
import json
from geopy.distance import geodesic

# Rutas predeterminadas
JSON_PATH = "Coords/cordenadas.json"
IMAGES_FOLDER = "Img"
VIDEOS_FOLDER = "Vids"
HTML_MAP_PATH = "Mapa/MapaFinal.html"
VELOCIDAD_PATH = "Velocidad/velocidades.json"

def guardar_segundos(grupos):
    segundos_json = {"grupos": []}
    for grupo in grupos:
        segundos = [p[0] for p in grupo]
        segundos_json["grupos"].append(segundos)
    os.makedirs(os.path.dirname(VELOCIDAD_PATH), exist_ok=True)
    with open(VELOCIDAD_PATH, "w") as f:
        json.dump(segundos_json, f, indent=4)

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
            lat1, lon1 = grupo[j][1], grupo[j][2]
            lat2, lon2 = grupo[j+1][1], grupo[j+1][2]
            tiempo_seg = segundos[j+1] - segundos[j]
            tiempo_h = tiempo_seg / 3600
            dist_km = geodesic((lat1, lon1), (lat2, lon2)).km
            if tiempo_h > 0:
                total_dist += dist_km
                total_tiempo_h += tiempo_h

        vel = total_dist / total_tiempo_h if total_tiempo_h > 0 else 0
        velocidades.append(round(vel, 2))

    return velocidades

def guardar_en_json(puntos_solo_coords):
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
    else:
        data = {"grupos": []}
    data["grupos"].append(puntos_solo_coords)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)

def generar_mapa(file_path=None, segundos_filtrados=None):
    print("Generando mapa...")

    if file_path:
        puntos = []

        with open(file_path, "r") as archivo:
            for linea in archivo:
                if "Segundo" in linea:
                    partes = linea.strip().split(":")
                    segundo = int(partes[0].split()[1])
                    coords = partes[1].split(",")
                    lat = float(coords[0].split("=")[1].strip())
                    lon = float(coords[1].split("=")[1].strip())
                    if segundos_filtrados is None or segundo in segundos_filtrados:
                        puntos.append([segundo, lat, lon])

        if not puntos:
            print("❌ No se encontraron puntos.")
            return
        else:
            puntos_solo_coords = [[lat, lon] for _, lat, lon in puntos]
            guardar_en_json(puntos_solo_coords)

        
        # Cargar grupos actuales y guardar segundos en JSON
        with open(JSON_PATH, "r") as f:
            coords_data = json.load(f)
            todos_los_grupos = coords_data.get("grupos", [])

        # Guardar segundos en base al nuevo grupo
        if os.path.exists(VELOCIDAD_PATH):
            with open(VELOCIDAD_PATH, "r") as f:
                segundos_json = json.load(f)
        else:
            segundos_json = {"grupos": []}
        segundos_grupos = segundos_json.get("grupos", [])
        segundos_grupos.append([p[0] for p in puntos])
        with open(VELOCIDAD_PATH, "w") as f:
            json.dump({"grupos": segundos_grupos}, f, indent=4)

    else:
        if not os.path.exists(JSON_PATH):
            print("❌ No existe el archivo de coordenadas.")
            return
        with open(JSON_PATH, "r") as f:
            coords_data = json.load(f)
            todos_los_grupos = coords_data.get("grupos", [])

    if not todos_los_grupos:
        print("❌ No hay puntos registrados para generar el mapa.")
        return

    # Cargar segundos y calcular velocidades
    if os.path.exists(VELOCIDAD_PATH):
        with open(VELOCIDAD_PATH, "r") as f:
            segundos_data = json.load(f).get("grupos", [])
    else:
        segundos_data = []

    velocidades = calcular_velocidades(
        [[(0, lat, lon) for lat, lon in grupo] for grupo in todos_los_grupos],
        segundos_data
    )

    # Crear mapa
    mapa = folium.Map(location=todos_los_grupos[0][0], zoom_start=18, tiles="OpenStreetMap")
    total_idx = 1

    for i, grupo in enumerate(todos_los_grupos):
        coords_js = [[lat, lon] for lat, lon in grupo]
        video_src = f"../vids/{i+1}.webm"

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
        polyline.add_child(folium.Popup(f'<a href="#" onclick="onClickGrupo{i}()">📹 Ver video</a>'))
        polyline.add_to(mapa)

        for lat, lon in grupo:
            img_path = os.path.join(IMAGES_FOLDER, f"{total_idx}.webp")
            if os.path.exists(img_path):
                html = f'''
                <div style="position: relative; width: 150px;">
                    <button onclick="mostrarImagen('../img/{total_idx}.webp')" style="
                        position: absolute;
                        top: 2px;
                        left: 2px;
                        padding: 2px 4px;
                        font-size: 10px;
                        border: none;
                        background-color: transparent;
                        border-radius: 3px;
                        cursor: pointer;
                        z-index: 10;
                    ">🔍</button>
                    <img src="../img/{total_idx}.webp" width="150px" style="display: block; border-radius: 4px;">
                </div>
                '''
                popup = folium.Popup(html, max_width=180)
            else:
                popup = folium.Popup("Imagen no encontrada", max_width=150)

            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color='blue',
                fill=True,
                fill_color='blue',
                fill_opacity=0.9,
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

    <script>
    function cerrarModal() {
        var modal = document.getElementById('videoModal');
        var video = document.getElementById('videoPlayer');
        video.pause();
        video.currentTime = 0;
        modal.style.display = 'none';
    }
    </script>
    """
    mapa.get_root().html.add_child(folium.Element(modal_html))

    # Modal de imagen ampliada
    imagen_modal = """
    <div id="imagenModal" style="
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
    ">
        <span onclick="cerrarImagenModal()" style="
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            z-index: 10001;">&times;</span>

        <img id="imagenAmpliada" src="" style="
            max-width: 90%;
            max-height: 90%;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
        ">
    </div>

    <script>
    function mostrarImagen(src) {
        var modal = document.getElementById('imagenModal');
        var img = document.getElementById('imagenAmpliada');
        img.src = src;
        modal.style.display = 'flex';
    }

    function cerrarImagenModal() {
        var modal = document.getElementById('imagenModal');
        modal.style.display = 'none';
    }
    </script>
    """
    mapa.get_root().html.add_child(folium.Element(imagen_modal))

    # Script para mostrar coordenadas al pasar el mouse por enxima
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

        const velocidades = """ + json.dumps(velocidades) + """;

        function mostrarDatos(index, e) {
            coordDiv.innerHTML =
                "📍 Lat: " + e.latlng.lat.toFixed(6) +
                "<br>📍 Lng: " + e.latlng.lng.toFixed(6) +
                "<br>🚗 Vel: " + velocidades[index] + " km/h";
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

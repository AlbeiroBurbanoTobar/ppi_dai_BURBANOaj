# importacion de librerias necesarias
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Torneo, User, Team
from . import db
import json
import pandas as pd
import os
import uuid 
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import numpy as np
import requests
import geopandas as gpd
from shapely.geometry import Point, box
from scipy import stats
from scipy.stats import pearsonr
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib
matplotlib.use('Agg')  # Usar el backend Agg
from sklearn.preprocessing import StandardScaler



views = Blueprint('views', __name__)



def generate_team_map(df_teams):
    """Genera un mapa con las ubicaciones de los equipos.

    Esta función toma un DataFrame de equipos, geocodifica sus ubicaciones,
    y genera un mapa con los puntos correspondientes. La imagen del mapa 
    se guarda en formato base64.

    Args:
        df_teams (pd.DataFrame): DataFrame que contiene las ubicaciones 
            de los equipos.

    Returns:
        str: Imagen del mapa en formato base64.
    """
    # Listas para almacenar las geometrías de los puntos y las direcciones
    geometry = []
    addresses = []

    # Iterar sobre cada ubicación en el DataFrame de equipos
    for location in df_teams['Location']:
        # Obtener las coordenadas de la ubicación
        coords = get_coordinates(location)
        if coords:
            # Si se obtienen coordenadas, crear un punto y agregar a la lista
            lat, lon = coords
            point = Point(lon, lat)
            geometry.append(point)
            addresses.append(location)
        else:
            # Si no se obtienen coordenadas, agregar None
            geometry.append(None)
            addresses.append(location)

    # Crear un GeoDataFrame con las geometrías
    gdf = gpd.GeoDataFrame(df_teams, geometry=geometry)

    # Cargar un mapa del mundo
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

    # Crear una figura y un eje para el gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    # Dibujar el mapa del mundo en color gris claro
    world.plot(ax=ax, color='lightgray')
    # Eliminar filas sin geometría
    gdf = gdf.dropna(subset=['geometry'])

    if not gdf.empty:
        # Si hay datos, dibujar los puntos en el mapa
        gdf.plot(ax=ax, color='blue', markersize=50, label='Equipos')

        # Ajustar los límites del mapa
        xlim = (gdf.geometry.x.min() - 5, gdf.geometry.x.max() + 5)
        ylim = (gdf.geometry.y.min() - 5, gdf.geometry.y.max() + 5)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
    else:
        # Si no hay datos, mostrar un mensaje
        ax.text(0.5, 0.5, 'No hay datos de equipos disponibles.', 
                horizontalalignment='center', 
                verticalalignment='center', 
                transform=ax.transAxes, 
                fontsize=12)

    # Añadir títulos y etiquetas
    plt.title('Ubicaciones de los Equipos')
    plt.xlabel('Longitud')
    plt.ylabel('Latitud')
    plt.legend()

    # Guardar la figura en un buffer en formato PNG
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    # Codificar la imagen en base64
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf8')
    buf.close()

    return image_base64



@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    """Renderiza la página principal del usuario y maneja la creación de notas.

    Si la solicitud es POST, se añade una nueva nota para el usuario actual. 
    Además, se cargan y procesan datos de partidos, jugadores y equipos para 
    generar estadísticas y visualizaciones que se muestran en la página.

    Returns:
        str: Plantilla HTML renderizada de la página principal.
    """
    if request.method == 'POST':
        # Obtiene la nota del formulario
        note = request.form.get('note')
        if len(note) < 1:
            flash('¡La nota es demasiado corta!', category='error')
        else:
            # Crea y guarda la nueva nota en la base de datos
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('¡Nota añadida!', category='success')

    # Rutas de los archivos CSV
    partidos_csv_path = 'Partidos.csv'
    players_csv_path = 'Players.csv'
    teams_csv_path = 'teams.csv'
    
    # Obtiene el user_id del usuario actual
    user_id = current_user.id

    # Inicialización de variables
    avg_time, earliest_time, latest_time, avg_age = None, None, None, None
    num_partidos, num_jugadores = 0, 0
    arbitros_img_base64, clusters_img_base64, team_map_base64 = None, None, None

    # Verifica si los archivos CSV existen
    if (os.path.exists(partidos_csv_path) and os.path.exists(players_csv_path) 
            and os.path.exists(teams_csv_path)):
        df_partidos = pd.read_csv(partidos_csv_path)
        df_players = pd.read_csv(players_csv_path)
        df_teams = pd.read_csv(teams_csv_path)

        # Asegura que el tipo de datos de user_id en los DataFrames sea consistente
        df_teams['UserID'] = df_teams['UserID'].astype(int)

        # Filtra equipos que pertenecen al usuario actual
        user_teams = df_teams[df_teams['UserID'] == user_id]

        # Genera el mapa de los equipos
        team_map_base64 = generate_team_map(user_teams)

        # Obtiene los TeamIDs de los equipos del usuario
        user_team_ids = user_teams['TeamID']

        # Filtra jugadores que pertenecen a los equipos del usuario actual
        user_players = df_players[df_players['TeamID'].isin(user_team_ids)]

        # Cuenta el número de jugadores del usuario
        num_jugadores = len(user_players)

        # Calcula el promedio de edad utilizando NumPy
        if not user_players.empty:
            avg_age = np.mean(user_players['Age'])
        else:
            avg_age = 0  # Si no hay jugadores, establece avg_age a 0

        # Filtra partidos que pertenecen a los equipos del usuario actual
        user_partidos = df_partidos[
            df_partidos['team_a'].isin(user_team_ids) | 
            df_partidos['team_b'].isin(user_team_ids)
        ]

        # Cuenta el número de partidos del usuario
        num_partidos = len(user_partidos)

        # Verifica si hay partidos del usuario
        if not user_partidos.empty:
            # Convierte la columna de tiempo a datetime
            user_partidos['match_time'] = pd.to_datetime(
                user_partidos['match_time'], format='%H:%M'
            )

            # Calcula el promedio de horarios utilizando NumPy
            times_in_seconds = (user_partidos['match_time'].dt.hour * 3600 + 
                                user_partidos['match_time'].dt.minute * 60)
            avg_time_seconds = np.mean(times_in_seconds)
            avg_hour = int(avg_time_seconds // 3600)
            avg_minute = int((avg_time_seconds % 3600) // 60)

            # Formatea el promedio de tiempo en HH:MM
            avg_time = f"{avg_hour:02d}:{avg_minute:02d}"

            # Calcula la hora más temprana y la más tardía
            earliest_time = user_partidos['match_time'].min().strftime('%H:%M')
            latest_time = user_partidos['match_time'].max().strftime('%H:%M')

            # Calcula la frecuencia de árbitros
            arbitros_freq = user_partidos['referee'].value_counts()

            # Crea la gráfica de barras horizontal con el color especificado
            plt.figure(figsize=(10, 6))
            arbitros_freq.plot(kind='barh', color='#007bff')
            plt.xlabel('Número de partidos')
            plt.ylabel('Árbitro')
            plt.title('Frecuencia de árbitros en los partidos')

            # Guarda la imagen en un buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            # Codificar la imagen en base64
            arbitros_img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            plt.close()

        # Fusionar datos de partidos con nombres de equipos
        user_partidos = user_partidos.merge(
            df_teams[['TeamID', 'TeamName']], 
            left_on='team_a', 
            right_on='TeamID', 
            how='left'
        )
        user_partidos.rename(columns={'TeamName': 'team_a_name'}, inplace=True)
        user_partidos = user_partidos.merge(
            df_teams[['TeamID', 'TeamName']], 
            left_on='team_b', 
            right_on='TeamID', 
            how='left'
        )
        user_partidos.rename(columns={'TeamName': 'team_b_name'}, inplace=True)

        # Crear etiquetas más descriptivas usando los nombres de los equipos
        user_partidos['team_names'] = (user_partidos['team_a_name'] + 
                                       ' vs ' + user_partidos['team_b_name'])

        # Aplica clustering jerárquico a los equipos basado en las puntuaciones 
        # y faltas
        features = ['team_a_score', 'team_b_score', 'faltas_team_a', 
                    'faltas_team_b']
        df_features = user_partidos[features].dropna()

        # Verifica si hay suficientes datos para escalar y aplicar clustering
        if not df_features.empty and len(df_features) > 1:
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(df_features)

            # Usa clustering jerárquico con SciPy
            linked = linkage(scaled_features, method='ward')

            # Crea el dendrograma con etiquetas más descriptivas
            plt.figure(figsize=(14, 8))
            dendrogram(
                linked,
                orientation='top',
                labels=list(user_partidos['team_names']),
                distance_sort='descending',
                show_leaf_counts=True
            )
            plt.title('Dendrograma de Equipos Basado en Puntuaciones y Faltas')
            plt.xlabel('Equipos')
            plt.ylabel('Distancia')
            plt.xticks(rotation=45, ha='right', fontsize=10)
            plt.tight_layout()

            # Guarda la imagen en un buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            # Codificar la imagen en base64
            clusters_img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            plt.close()

    return render_template(
        "home.html", 
        user=current_user, 
        avg_time=avg_time, 
        earliest_time=earliest_time, 
        latest_time=latest_time, 
        avg_age=avg_age, 
        user_id=user_id, 
        num_partidos=num_partidos, 
        num_jugadores=num_jugadores, 
        arbitros_img_base64=arbitros_img_base64, 
        clusters_img_base64=clusters_img_base64, 
        team_map_base64=team_map_base64
    )


@views.route('/guest')
def guest():
    """Renderiza la página de invitados con información sobre torneos,
    partidos y análisis de datos.

    Returns:
        str: Plantilla HTML renderizada de la página de invitados.
    """
    from .models import Torneo  # Importación dentro de la función para evitar ciclos

    # Obtener todos los torneos
    torneos = Torneo.query.all()
    print(f"Torneos: {torneos}")

    # Cargar los datos de los equipos
    teams_csv_path = 'teams.csv'
    teams = {}
    if os.path.exists(teams_csv_path):
        df_teams = pd.read_csv(teams_csv_path)
        print(f"Equipos cargados: {df_teams.head()}")
        teams = df_teams.set_index('TeamID')['TeamName'].to_dict()

    # Cargar los datos de los partidos
    partidos_csv_path = 'Partidos.csv'
    matches = []
    if os.path.exists(partidos_csv_path):
        df_matches = pd.read_csv(partidos_csv_path)
        print(f"Partidos cargados: {df_matches.head()}")
        df_matches['team_a'] = df_matches['team_a'].map(teams)
        df_matches['team_b'] = df_matches['team_b'].map(teams)
        today = datetime.today().date()
        df_matches['match_date'] = pd.to_datetime(df_matches['match_date']).dt.date

        # Filtrar partidos pasados (que ya se han jugado)
        df_matches = df_matches[df_matches['match_date'] < today]
        print(f"Partidos filtrados por fecha pasada: {df_matches.head()}")
        matches = df_matches.to_dict(orient='records')

    # Análisis de Correlación con scipy
    correlation_image_base64 = None
    if not df_matches.empty:
        # Calcular las características agregadas por equipo
        team_stats = df_matches.groupby('team_a').agg({
            'team_a_score': 'mean',
            'faltas_team_a': 'mean'
        }).reset_index()

        # Renombrar columnas para claridad
        team_stats.columns = ['TeamID', 'AvgScore', 'AvgFouls']
        print(f"Estadísticas del equipo: {team_stats}")

        # Verificar que no haya valores NaN y que haya más de un equipo
        if not team_stats[['AvgScore', 'AvgFouls']].isnull().values.any() and len(team_stats) > 1:
            # Calcular la correlación de Pearson con scipy
            corr_coef, p_value = pearsonr(team_stats['AvgScore'], team_stats['AvgFouls'])
            print(f"Coeficiente de Pearson: {corr_coef}, p-value: {p_value}")
            
            # Crear el mapa de calor de correlación
            plt.figure(figsize=(8, 6))
            sns.heatmap(team_stats[['AvgScore', 'AvgFouls']].corr(), annot=True, cmap='coolwarm', vmin=-1, vmax=1, center=0, linewidths=.5)
            plt.title(f'Mapa de Calor de Correlación (Coeficiente de Pearson: {corr_coef:.2f}, p-value: {p_value:.2f})')

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            correlation_image_base64 = base64.b64encode(buf.getvalue()).decode('utf8')
            buf.close()
        else:
            print("No hay suficientes datos para calcular la correlación.")
            correlation_image_base64 = None

    # Gráfica de distribución de partidos por fecha
    if not df_matches.empty:
        match_dates = df_matches['match_date'].value_counts().sort_index()
        fig, ax = plt.subplots()
        match_dates.plot(kind='line', ax=ax, marker='o', color='#007bff')
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Número de Partidos')
        ax.set_title('Distribución de Partidos por Fecha')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf8')
        buf.close()
    else:
        image_base64 = None

    # Gráfica de distribución de equipos por categoría
    if not df_teams.empty:
        category_counts = df_teams['Category'].value_counts()
        fig2, ax2 = plt.subplots()
        colors = ['#007bff' if category == 'Masculino' else '#ff69b4' for category in category_counts.index]
        category_counts.plot(kind='bar', ax=ax2, color=colors)
        ax2.set_xlabel('Categoría')
        ax2.set_ylabel('Número de Equipos')
        ax2.set_title('Distribución de Equipos por Categoría')
        plt.xticks(rotation=0, ha='center')

        buf2 = io.BytesIO()
        plt.savefig(buf2, format='png')
        buf2.seek(0)
        category_image_base64 = base64.b64encode(buf2.getvalue()).decode('utf8')
        buf2.close()
    else:
        category_image_base64 = None

    # Renderizar la plantilla HTML con todos los datos calculados
    return render_template(
        'guest.html', user=current_user, torneos=torneos, matches=matches,
        image_base64=image_base64, category_image_base64=category_image_base64,
        correlation_image_base64=correlation_image_base64
    )


@views.route('/delete-note', methods=['POST'])
def delete_note():
    """Elimina una nota de la base de datos.

    Esta función espera un objeto JSON desde el archivo "index.js",
    con una propiedad 'noteId'. Luego recupera la nota con el ID
    proporcionado y, si pertenece al usuario actual, la elimina de
    la base de datos.

    Returns:
        dict: Un objeto JSON vacío.
    """
    note_data = json.loads(request.data)
    note_id = note_data['noteId']
    note = Note.query.get(note_id)

    if note and note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()

    return jsonify({})


@views.route('/tournaments')
@login_required
def tournaments():
    """Renderiza la plantilla 'tournaments.html', 
    pasando al usuario actual.

    Returns:
        str: La plantilla a renderizar.
    """
    return render_template('tournaments.html', user=current_user)


@views.route('/teams')
@login_required
def teams():
    """Renderiza la página de equipos del usuario actual.

    Esta función carga los datos de los equipos y jugadores desde archivos
    CSV, cuenta el número de jugadores por equipo y filtra los equipos que
    pertenecen al usuario actual.

    Returns:
        str: Plantilla HTML renderizada de la página de equipos.
    """
    # Rutas de los archivos CSV
    csv_file_path_teams = 'teams.csv'
    csv_file_path_players = 'Players.csv'
    
    # Verifica si el archivo de equipos existe
    if os.path.exists(csv_file_path_teams):

        # Cargar datos de equipos
        df_teams = pd.read_csv(csv_file_path_teams)

        # Cargar datos de jugadores si el archivo existe, de lo contrario un DataFrame vacío
        df_players = (pd.read_csv(csv_file_path_players) if os.path.exists(
            csv_file_path_players) else pd.DataFrame())
        
        # Contar los jugadores para cada equipo
        player_counts = df_players.groupby('TeamID').size().rename(
            'PlayerCount').reset_index()
        
        # Fusionar el conteo de jugadores con los datos de equipos
        df_teams = df_teams.merge(player_counts, how='left', 
                                  left_on='TeamID', right_on='TeamID')
        df_teams['PlayerCount'] = df_teams['PlayerCount'].fillna(0).astype(int)
        
        # Filtrar los equipos que pertenecen al usuario actual
        filtered_teams = df_teams[df_teams['UserID'] == current_user.id].to_dict(
            orient='records')
    else:

        # Si no existe el archivo de equipos, la lista de equipos filtrados está vacía
        filtered_teams = []
    
    # Renderizar la plantilla HTML con los datos de equipos filtrados
    return render_template('teams.html', user=current_user, teams=filtered_teams)




@views.route('/calendar')
@login_required
def calendar():
    """Renderiza la plantilla 'calendar.html', pasando al usuario actual y la
    lista de partidos desde el archivo CSV.

    Returns:
        str: La plantilla HTML renderizada.
    """
    # Ruta del archivo CSV de partidos
    csv_file_path = 'partidos.csv'
    matches = []

    # Verifica si el archivo CSV existe
    if os.path.exists(csv_file_path):

        # Leer los datos de los partidos desde el archivo CSV
        df = pd.read_csv(csv_file_path)

        # Convertir los datos de los partidos a una lista de diccionarios
        matches = df[['match_date', 'tournament_name']].to_dict(orient='records')
    
    # Renderizar la plantilla HTML con los datos de los partidos
    return render_template('calendar.html', user=current_user, matches=matches)

@views.route('/create-tournament', methods=['POST'])
@login_required
def create_tournament():
    """Crea un nuevo torneo y lo añade a la base de datos.

    Recupera los datos del torneo del formulario, verifica si
    todos los campos están completos, y luego añade el nuevo
    torneo a la base de datos.

    Returns:
        werkzeug.wrappers.response.Response: Redirige a la plantilla de torneos.
    """
    # Obtener datos del formulario
    nombre = request.form.get('tournamentName')
    fecha_inicio = request.form.get('startDate')
    fecha_final = request.form.get('endDate')
    deporte = request.form.get('sport')
    equipos_participantes = request.form.get('teams')

    # Verificar que todos los campos estén completos
    if not (nombre and fecha_inicio and fecha_final and deporte 
            and equipos_participantes):
        flash('Todos los campos son requeridos.', 'error')
        return redirect(url_for('views.tournaments'))

    # Crear un nuevo torneo
    nuevo_torneo = Torneo(
        nombre=nombre,
        fecha_inicio=fecha_inicio,
        fecha_final=fecha_final,
        deporte=deporte,
        equipos_participantes=equipos_participantes,
        user_id=current_user.id
    )

    # Añadir el nuevo torneo a la base de datos
    db.session.add(nuevo_torneo)
    db.session.commit()

    flash('Torneo creado con éxito.', 'success')
    return redirect(url_for('views.tournaments'))

@views.route('/get-tournaments')
@login_required
def get_tournaments():
    """Recupera y devuelve los torneos asociados al usuario actual en forma de
    JSON.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con la lista de 
        diccionarios con los datos de los torneos.
    """
    # Obtener los torneos asociados al usuario actual
    torneos = Torneo.query.filter_by(user_id=current_user.id).all()

    # Convertir los datos de los torneos a una lista de diccionarios
    torneos_data = [{
        'id': torneo.id,
        'nombre': torneo.nombre,
        'fecha_inicio': torneo.fecha_inicio,
        'fecha_final': torneo.fecha_final,
        'deporte': torneo.deporte,
        'equipos_participantes': torneo.equipos_participantes,
    } for torneo in torneos]

    # Devolver los datos de los torneos en formato JSON
    return jsonify(torneos_data)


@views.route('/create-team', methods=['POST'])
@login_required
def create_team():
    """Crea un nuevo equipo y lo guarda en la base de datos y en un archivo CSV.

    Esta función recupera los datos del formulario enviado por el usuario,
    verifica que todos los campos estén completos, asigna un nuevo ID de equipo,
    guarda el equipo en la base de datos y en un archivo CSV.

    Returns:
        werkzeug.wrappers.response.Response: Redirige a la página de equipos.
    """
    # Recuperar datos del formulario
    team_name = request.form.get('teamName')
    captain_name = request.form.get('captainName')
    captain_contact = request.form.get('captainContact')
    category = request.form.get('category')
    location = request.form.get('location')

    # Verificar que todos los campos estén presentes
    if not (team_name and captain_name and captain_contact and category 
            and location):
        flash('Todos los campos son requeridos.', 'error')
        return redirect(url_for('views.teams'))

    # Leer el archivo CSV si existe
    csv_file_path = 'teams.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        if df.empty:
            team_id = 1
        else:
            # Obtener el ID de equipo más alto y asignar el siguiente
            max_team_id = df['TeamID'].apply(
                lambda x: int(x.split('-')[1])
            ).max()
            team_id = max_team_id + 1
    else:

        # Crear un nuevo DataFrame si el archivo no existe
        df = pd.DataFrame(columns=[
            'TeamID', 'UserID', 'TeamName', 'CaptainName', 'CaptainContact', 
            'Category', 'Location'
        ])
        team_id = 1

    # ID del usuario actual
    user_id = current_user.id

    # Formatear el nuevo TeamID como un número entero
    team_id = f"{user_id}-{team_id}"

    # Añadir el nuevo equipo a la base de datos
    nuevo_equipo = Team(
        nombre=team_name,
        capitan=captain_name,
        contacto=captain_contact,
        categoria=category,
        ubicacion=location,
        user_id=user_id
    )

    db.session.add(nuevo_equipo)
    db.session.commit()

    # Añadir la nueva fila al DataFrame
    new_row = pd.DataFrame([{
        'TeamID': team_id,
        'UserID': user_id,
        'TeamName': team_name,
        'CaptainName': captain_name,
        'CaptainContact': captain_contact,
        'Category': category,
        'Location': location
    }])

    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(csv_file_path, index=False)

    flash('Equipo creado con éxito.', 'success')
    return redirect(url_for('views.teams'))


def generate_next_id(csv_file_path):
    """Genera el siguiente ID disponible para un nuevo registro en un archivo CSV.

    Esta función lee un archivo CSV y genera el siguiente ID disponible
    basado en la columna 'PlayerID'. Si el archivo no existe o está vacío,
    el ID devuelto será 1.

    Args:
        csv_file_path (str): La ruta del archivo CSV.

    Returns:
        int: El siguiente ID disponible.
    """
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        if df.empty:
            return 1
        else:
            return df['PlayerID'].max() + 1
    else:
        return 1

@views.route('/add-player', methods=['POST'])
@login_required
def add_player():
    """Añade un nuevo jugador y lo guarda en un archivo CSV.

    Esta función recupera los datos del formulario enviado por el usuario,
    genera un nuevo ID para el jugador, y guarda la información en el archivo
    CSV 'Players.csv'.

    Returns:
        werkzeug.wrappers.response.Response: Redirige a la página de equipos.
    """
    # Recuperar datos del formulario
    player_first_name = request.form.get('playerFirstName')
    player_last_name = request.form.get('playerLastName')
    player_age = request.form.get('playerAge')
    team_id = request.form.get('teamId')

    # Ruta del archivo CSV de jugadores
    csv_file_path = 'Players.csv'
    # Generar el próximo ID para el jugador
    player_id = generate_next_id(csv_file_path)

    # Crear un diccionario con los datos del jugador
    player_data = {
        'PlayerID': player_id,
        'FirstName': player_first_name,
        'LastName': player_last_name,
        'Age': player_age,
        'TeamID': team_id
    }

    # Verificar si el archivo CSV existe
    if os.path.exists(csv_file_path):
        # Leer el archivo CSV y añadir el nuevo jugador
        df = pd.read_csv(csv_file_path)
        new_row = pd.DataFrame([player_data])
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        # Crear un nuevo DataFrame si el archivo no existe
        df = pd.DataFrame([player_data])

    # Guardar los datos actualizados en el archivo CSV
    df.to_csv(csv_file_path, index=False)
    
    # Mostrar un mensaje de éxito
    flash('Jugador creado exitosamente', 'success')
    
    # Redirigir a la página de equipos
    return redirect(url_for('views.teams'))


@views.route('/get-user-tournaments', methods=['GET'])
@login_required
def get_user_tournaments():
    """Recupera y devuelve los torneos asociados al usuario actual en forma de
    JSON.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con los datos 
        de los torneos.
    """
    # Obtener los torneos asociados al usuario actual
    torneos = Torneo.query.filter_by(user_id=current_user.id).all()
    # Convertir los datos de los torneos a una lista de diccionarios
    torneos_data = [{'id': torneo.id, 'nombre': torneo.nombre} 
                    for torneo in torneos]
    # Devolver los datos de los torneos en formato JSON
    return jsonify(torneos_data)

@views.route('/get-user-teams', methods=['GET'])
@login_required
def get_user_teams():
    """Devuelve los equipos asociados al usuario actual en forma de JSON.

    Esta función lee un archivo CSV que contiene los equipos, filtra los 
    equipos que pertenecen al usuario actual y devuelve una lista de 
    diccionarios con los IDs y nombres de los equipos en formato JSON.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con los datos 
        de los equipos o una lista vacía.
    """
    # Ruta del archivo CSV de equipos
    csv_file_path = 'teams.csv'
    
    # Verificar si el archivo CSV existe
    if os.path.exists(csv_file_path):

        # Leer el archivo CSV
        df = pd.read_csv(csv_file_path)

        # Filtrar los equipos que pertenecen al usuario actual
        filtered_teams = df[df['UserID'] == current_user.id]

        # Convertir los equipos filtrados a una lista de diccionarios
        teams_data = filtered_teams.to_dict(orient='records')

        # Formatear los datos de los equipos
        teams_formatted = [{'id': team['TeamID'], 'name': team['TeamName']} 
                           for team in teams_data]
        
        # Devolver los datos de los equipos en formato JSON
        return jsonify(teams_formatted)
    else:

        # Devolver una lista vacía si no hay archivo o no hay equipos
        return jsonify([])

@views.route('/schedule-match', methods=['POST'])
@login_required
def schedule_match():
    """Programa un nuevo partido y lo guarda en un archivo CSV.

    Esta función recupera los datos del formulario enviado por el usuario,
    crea un identificador único para el partido, guarda la información en 
    el archivo CSV 'Partidos.csv' y redirige al calendario de partidos.

    Returns:
        werkzeug.wrappers.response.Response: Redirige a la página de 
        calendario o a la página de inicio.
    """
    if request.method == 'POST':

        # Recuperar datos del formulario
        tournament_id = request.form.get('tournamentSelect')
        team_a = request.form.get('teamA')
        team_b = request.form.get('teamB')
        match_date = request.form.get('date')
        referee = request.form.get('referee')
        location = request.form.get('location')
        categoria = request.form.get('categoria')
        match_time = request.form.get('match_time')

        # Obtener el nombre del torneo basado en el ID
        torneo = Torneo.query.filter_by(
            id=tournament_id, user_id=current_user.id
        ).first()
        tournament_name = torneo.nombre if torneo else "Unknown Tournament"

        # Crear un identificador único para cada partido
        match_id = str(uuid.uuid4())

        # Información del usuario que programa el partido
        user_id = current_user.id

        # Definir la ruta del archivo CSV
        csv_file_path = 'Partidos.csv'

        # Crear un DataFrame con los datos del formulario
        data = pd.DataFrame({
            'match_id': [match_id],
            'user_id': [user_id],
            'tournament_name': [tournament_name],
            'team_a': [team_a],
            'team_b': [team_b],
            'match_date': [match_date],
            'referee': [referee],
            'match_time': [match_time],
            'location': [location],
            'categoria': [categoria],
            'team_a_score': [0],
            'team_b_score': [0],
            'faltas_team_a': [0],
            'faltas_team_b': [0],
        })

        # Guardar o agregar al archivo CSV existente
        if os.path.exists(csv_file_path):
            df = pd.read_csv(csv_file_path)
            df = pd.concat([df, data], ignore_index=True)
        else:
            df = data

        # Guardar el DataFrame actualizado en el archivo CSV
        df.to_csv(csv_file_path, index=False)

        # Mostrar un mensaje de éxito
        flash('Partido programado con éxito!', 'success')
        
        # Redirigir a la página del calendario
        return redirect(url_for('views.calendar'))
    
    # Redirigir a la página de inicio si la solicitud no es POST
    return redirect(url_for('views.home'))

@views.route('/get-team-names', methods=['GET'])
def get_team_names():
    """Devuelve los nombres de los equipos en formato JSON.

    Esta función lee un archivo CSV que contiene los equipos y devuelve
    una lista de diccionarios con los IDs y nombres de los equipos en 
    formato JSON. Si ocurre un error, devuelve un mensaje de error en 
    formato JSON.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con los datos 
        de los equipos o un mensaje de error.
    """
    try:
        # Leer el archivo CSV de equipos
        teams_df = pd.read_csv('teams.csv')

        # Seleccionar las columnas relevantes y convertir a lista de diccionarios
        teams = teams_df[['TeamID', 'TeamName']].to_dict(orient='records')

        # Devolver los datos de los equipos en formato JSON
        return jsonify(teams)
    except Exception as e:

        # Devolver un mensaje de error en formato JSON si ocurre una excepción
        return jsonify({'error': str(e)}), 500

@views.route('/get-matches', methods=['GET'])
@login_required
def get_matches():
    """Devuelve los partidos creados por el usuario actual en formato JSON.

    Esta función lee los archivos CSV que contienen los partidos y equipos,
    filtra los partidos para incluir solo los creados por el usuario actual,
    y devuelve una lista de diccionarios con los datos de los partidos en 
    formato JSON. Si ocurre un error, devuelve un mensaje de error en formato 
    JSON.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con los datos 
        de los partidos o un mensaje de error.
    """
    try:
        # Leer los archivos CSV de partidos y equipos
        matches_df = pd.read_csv('Partidos.csv')
        teams_df = pd.read_csv('teams.csv')
        
        # Filtrar los partidos para incluir solo los creados por el usuario actual
        matches_df = matches_df[matches_df['user_id'] == current_user.id]
        
        # Crear un diccionario para mapear TeamID a TeamName
        team_names = teams_df.set_index('TeamID')['TeamName'].to_dict()
        
        # Mapear los IDs de los equipos a sus nombres
        matches_df['team_a_name'] = matches_df['team_a'].map(team_names).fillna(matches_df['team_a'])
        matches_df['team_b_name'] = matches_df['team_b'].map(team_names).fillna(matches_df['team_b'])
        
        # Convertir los datos de los partidos a una lista de diccionarios
        matches = matches_df.to_dict(orient='records')
        
        # Devolver los datos de los partidos en formato JSON
        return jsonify(matches)
    except Exception as e:
        # Devolver un mensaje de error en formato JSON si ocurre una excepción
        return jsonify({'error': str(e)}), 500

@views.route('/get-teams/<categoria>', methods=['GET'])
@login_required
def get_teams(categoria):
    """Devuelve los equipos del usuario actual filtrados por categoría en 
    formato JSON.

    Esta función lee un archivo CSV que contiene los equipos, filtra los 
    equipos que pertenecen al usuario actual y a la categoría especificada, 
    y devuelve una lista de diccionarios con los IDs y nombres de los equipos 
    en formato JSON.

    Args:
        categoria (str): Categoría por la cual filtrar los equipos.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con los datos 
        de los equipos filtrados o una lista vacía.
    """
    # Ruta del archivo CSV de equipos
    csv_file_path = 'teams.csv'
    
    # Verificar si el archivo CSV existe
    if os.path.exists(csv_file_path):
        # Leer el archivo CSV
        df = pd.read_csv(csv_file_path)

        # Filtrar los equipos que pertenecen al usuario actual y a la categoría especificada
        filtered_teams = df[(df['UserID'] == current_user.id) & 
                            (df['Category'] == categoria)]
        
        # Convertir los equipos filtrados a una lista de diccionarios
        teams_data = filtered_teams.to_dict(orient='records')
        # Formatear los datos de los equipos
        teams_formatted = [{'id': team['TeamID'], 'name': team['TeamName']} 
                           for team in teams_data]
        
        # Devolver los datos de los equipos en formato JSON
        return jsonify(teams_formatted)
    else:

        # Devolver una lista vacía si no hay archivo o no hay equipos
        return jsonify([])

@views.route('/update-match', methods=['POST'])
@login_required
def update_match():
    """Actualiza la información de un partido en el archivo CSV.

    Esta función recibe los datos actualizados de un partido desde una 
    solicitud POST, busca el partido en el archivo CSV 'Partidos.csv' y 
    actualiza sus datos. Si el partido no se encuentra, devuelve un 
    mensaje de error.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON indicando 
        el éxito o fracaso de la actualización.
    """
    # Obtener los datos de la solicitud JSON
    data = request.get_json()
    
    # Ruta del archivo CSV de partidos
    csv_file_path = 'Partidos.csv'
    
    # Verificar si el archivo CSV existe
    if os.path.exists(csv_file_path):
        # Leer el archivo CSV
        df = pd.read_csv(csv_file_path)
        
        # Obtener el ID del partido y buscar el índice correspondiente
        match_id = data['match_id']
        match_index = df[df['match_id'] == match_id].index
        
        # Verificar si el partido existe
        if not match_index.empty:
            match_index = match_index[0]
            # Actualizar los datos del partido
            df.at[match_index, 'team_a_score'] = data['team_a_score']
            df.at[match_index, 'team_b_score'] = data['team_b_score']
            df.at[match_index, 'faltas_team_a'] = data['faltas_team_a']
            df.at[match_index, 'faltas_team_b'] = data['faltas_team_b']
            
            # Guardar los datos actualizados en el archivo CSV
            df.to_csv(csv_file_path, index=False)
            return jsonify({'success': True})
        
    # Devolver un mensaje de error si el partido no se encuentra
    return jsonify({'success': False, 'message': 'Partido no encontrado'}), 404

@views.route('/get-tournament-info/<tournament_name>')
def get_tournament_info(tournament_name):
    """Devuelve información sobre un torneo en formato JSON.

    Esta función carga los archivos CSV que contienen los partidos y equipos,
    filtra los partidos por el nombre del torneo, reemplaza los IDs de los 
    equipos por sus nombres y calcula las medias de puntuaciones y faltas.
    Devuelve una lista de diccionarios con los datos de los partidos en 
    formato JSON.

    Args:
        tournament_name (str): Nombre del torneo.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con los datos 
        de los partidos o un mensaje de error.
    """
    # Ruta del archivo CSV de partidos
    partidos_csv_path = 'Partidos.csv'

    # Ruta del archivo CSV de equipos
    teams_csv_path = 'teams.csv'
    
    # Cargar nombres de equipos
    if os.path.exists(teams_csv_path):
        df_teams = pd.read_csv(teams_csv_path)
        teams_dict = df_teams.set_index('TeamID')['TeamName'].to_dict()
    else:
        teams_dict = {}

    # Cargar y filtrar partidos
    if os.path.exists(partidos_csv_path):
        df_matches = pd.read_csv(partidos_csv_path)
        # Filtrar partidos por el nombre del torneo
        df_matches = df_matches[df_matches['tournament_name'] == tournament_name]

        # Reemplazar IDs de equipos por nombres
        df_matches['team_a'] = df_matches['team_a'].map(teams_dict)
        df_matches['team_b'] = df_matches['team_b'].map(teams_dict)

        # Calcular medias de puntuaciones y faltas
        df_matches['media_puntuacion'] = df_matches[['team_a_score', 
                                                     'team_b_score']].mean(
            axis=1)
        df_matches['media_faltas'] = df_matches[['faltas_team_a', 
                                                 'faltas_team_b']].mean(
            axis=1)

        # Convertir los datos de los partidos a una lista de diccionarios
        matches = df_matches.to_dict(orient='records')
    else:
        matches = []

    # Devolver los datos de los partidos en formato JSON
    return jsonify(matches=matches)


def get_coordinates(address):
    """Obtiene las coordenadas geográficas (latitud y longitud) de una dirección.

    Esta función envía una solicitud a la API de Nominatim de OpenStreetMap para 
    obtener las coordenadas geográficas de una dirección proporcionada.

    Args:
        address (str): La dirección para la cual se desean obtener las coordenadas.

    Returns:
        tuple: Una tupla con la latitud y longitud (lat, lon) si se encuentra la 
        dirección, de lo contrario None.
    """
    # URL de la API de Nominatim
    url = 'https://nominatim.openstreetmap.org/search'

    # Parámetros de la solicitud
    params = {'q': address, 'format': 'json'}

    # Encabezados de la solicitud
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (compatible; my bot/0.1; +http://mywebsite.com/bot)'
        )
    }

    try:
        # Realizar la solicitud GET a la API
        response = requests.get(url, params=params, headers=headers)

        # Levantar una excepción para errores HTTP
        response.raise_for_status()
        
        # Decodificar la respuesta JSON
        data = response.json()
        if data:

            # Obtener latitud y longitud de los resultados
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
        else:
            print("No se encontraron resultados para la dirección proporcionada.")
            return None
    except requests.exceptions.RequestException as e:

        # Manejar errores en la solicitud HTTP
        print(f"Error en la solicitud HTTP: {e}")
        return None
    except ValueError as e:

        # Manejar errores al decodificar la respuesta JSON
        print(f"Error al decodificar la respuesta JSON: {e}")
        return None

def generate_map(address):
    """Genera un mapa con la ubicación de una dirección geocodificada.

    Esta función obtiene las coordenadas geográficas de una dirección 
    proporcionada, crea un punto en esas coordenadas, y genera un mapa 
    que muestra ese punto. La imagen del mapa se guarda como una imagen 
    codificada en base64.

    Args:
        address (str): La dirección para la cual se desea generar el mapa.

    Returns:
        str: Una cadena codificada en base64 que representa la imagen del mapa.
        None: Si no se pueden obtener las coordenadas de la dirección.
    """
    # Obtener las coordenadas de la dirección
    coords = get_coordinates(address)
    if coords:
        lat, lon = coords

        # Crear un punto geográfico con las coordenadas obtenidas
        point = Point(lon, lat)
        gdf = gpd.GeoDataFrame([{'geometry': point, 'address': address}])

        # Cargar directamente un archivo GeoJSON desde GitHub
        url = ('https://raw.githubusercontent.com/johan/world.geo.json/'
               'master/countries.geo.json')
        world = gpd.read_file(url)

        # Crear una caja delimitadora alrededor de las coordenadas
        buffer = 0.1  # Grados de latitud y longitud para la caja delimitadora
        bbox = box(lon - buffer, lat - buffer, lon + buffer, lat + buffer)

        # Filtrar el GeoDataFrame para incluir solo los países dentro de la caja
        world = world[world.intersects(bbox)]

        # Crear la figura del mapa
        ax = world.plot(figsize=(10, 6))
        gdf.plot(ax=ax, color='red', markersize=100)
        ax.set_title('Mapa con dirección geocodificada')

        # Guardar la figura en un buffer en formato PNG
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Codificar la imagen en base64
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf8')
        buf.close()

        return image_base64
    else:
        print("No se pudieron obtener las coordenadas.")
        return None

@views.route('/get-map/<address>', methods=['GET'])
def get_map(address):
    """Genera un mapa basado en la dirección proporcionada y lo devuelve como 
    una imagen codificada en base64.

    Esta función utiliza la dirección proporcionada para generar un mapa con 
    su ubicación geocodificada. Si la generación del mapa es exitosa, devuelve 
    la imagen codificada en base64. Si no, devuelve un mensaje de error.

    Args:
        address (str): La dirección para la cual se desea generar el mapa.

    Returns:
        werkzeug.wrappers.response.Response: Respuesta JSON con la imagen 
        del mapa en base64 o un mensaje de error.
    """
    # Generar el mapa basado en la dirección proporcionada
    map_image = generate_map(address)
    
    # Verificar si se generó la imagen del mapa
    if map_image:
        
        # Devolver la imagen codificada en base64 en formato JSON
        return jsonify({'image_base64': map_image})
    else:

        # Devolver un mensaje de error si no se pudieron obtener las coordenadas
        return jsonify({'error': 'No se pudieron obtener las coordenadas.'}), 500





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




views = Blueprint('views', __name__)



@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        note = request.form.get('note')
        if len(note) < 1:
            flash('¡La nota es demasiado corta!', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('¡Nota añadida!', category='success')

    # Cargar archivos CSV
    partidos_csv_path = 'Partidos.csv'
    players_csv_path = 'Players.csv'
    teams_csv_path = 'teams.csv'
    
    # Obtener el user_id del usuario actual
    user_id = current_user.id

    avg_time, earliest_time, latest_time, avg_age = None, None, None, None
    num_partidos, num_jugadores = 0, 0
    arbitros_img_base64 = None

    if os.path.exists(partidos_csv_path) and os.path.exists(players_csv_path) and os.path.exists(teams_csv_path):
        df_partidos = pd.read_csv(partidos_csv_path)
        df_players = pd.read_csv(players_csv_path)
        df_teams = pd.read_csv(teams_csv_path)

        # Asegurarse de que el tipo de datos de user_id en los DataFrames sea consistente
        df_teams['UserID'] = df_teams['UserID'].astype(int)

        # Filtrar equipos que pertenecen al usuario actual
        user_teams = df_teams[df_teams['UserID'] == user_id]

        # Obtener los TeamIDs de los equipos del usuario
        user_team_ids = user_teams['TeamID']

        # Filtrar jugadores que pertenecen a los equipos del usuario actual
        user_players = df_players[df_players['TeamID'].isin(user_team_ids)]

        # Contar el número de jugadores del usuario
        num_jugadores = len(user_players)

        # Calcular el promedio de edad utilizando NumPy
        if not user_players.empty:
            avg_age = np.mean(user_players['Age'])
        
        # Filtrar partidos que pertenecen al usuario actual
        df_partidos['user_id'] = df_partidos['user_id'].astype(int)
        user_partidos = df_partidos[df_partidos['user_id'] == user_id]

        # Contar el número de partidos del usuario
        num_partidos = len(user_partidos)

        # Verificar si hay partidos del usuario
        if not user_partidos.empty:
            # Convertir la columna de tiempo a datetime
            user_partidos['match_time'] = pd.to_datetime(user_partidos['match_time'], format='%H:%M')

            # Calcular el promedio de horarios utilizando NumPy
            times_in_seconds = user_partidos['match_time'].dt.hour * 3600 + user_partidos['match_time'].dt.minute * 60
            avg_time_seconds = np.mean(times_in_seconds)
            avg_hour = int(avg_time_seconds // 3600)
            avg_minute = int((avg_time_seconds % 3600) // 60)

            # Formatear el promedio de tiempo en HH:MM
            avg_time = f"{avg_hour:02d}:{avg_minute:02d}"

            # Calcular la hora más temprana y la más tardía
            earliest_time = user_partidos['match_time'].min().strftime('%H:%M')
            latest_time = user_partidos['match_time'].max().strftime('%H:%M')

            # Calcular la frecuencia de árbitros
            arbitros_freq = user_partidos['referee'].value_counts()

            # Crear la gráfica de barras horizontal con el color especificado
            plt.figure(figsize=(10, 6))
            arbitros_freq.plot(kind='barh', color='#007bff')
            plt.xlabel('Número de partidos')
            plt.ylabel('Árbitro')
            plt.title('Frecuencia de árbitros en los partidos')

            # Guardar la imagen en un buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            # Codificar la imagen en base64
            arbitros_img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            plt.close()

    return render_template("home.html", user=current_user, avg_time=avg_time, earliest_time=earliest_time, latest_time=latest_time, avg_age=avg_age, user_id=user_id, num_partidos=num_partidos, num_jugadores=num_jugadores, arbitros_img_base64=arbitros_img_base64)


@views.route('/guest')
def guest():
    torneos = Torneo.query.all()
    
    # Cargar los datos de los equipos
    teams_csv_path = 'teams.csv'
    teams = {}
    if os.path.exists(teams_csv_path):
        df_teams = pd.read_csv(teams_csv_path)
        teams = df_teams.set_index('TeamID')['TeamName'].to_dict()

    # Cargar los datos de los partidos
    partidos_csv_path = 'Partidos.csv'
    matches = []
    if os.path.exists(partidos_csv_path):
        df_matches = pd.read_csv(partidos_csv_path)
        df_matches['team_a'] = df_matches['team_a'].map(teams)
        df_matches['team_b'] = df_matches['team_b'].map(teams)
        today = datetime.today().date()
        df_matches['match_date'] = pd.to_datetime(df_matches['match_date']).dt.date
        df_matches = df_matches[df_matches['match_date'] >= today]
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

        # Verificar que no haya valores NaN y que haya más de un equipo
        if not team_stats[['AvgScore', 'AvgFouls']].isnull().values.any() and len(team_stats) > 1:
            # Calcular la correlación de Pearson con scipy
            corr_coef, p_value = pearsonr(team_stats['AvgScore'], team_stats['AvgFouls'])
            
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
            correlation_image_base64 = None

    # Gráfica de distribución de partidos por fecha
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

    return render_template('guest.html', user=current_user, torneos=torneos, matches=matches, image_base64=image_base64, category_image_base64=category_image_base64, correlation_image_base64=correlation_image_base64)


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
    csv_file_path_teams = 'teams.csv'
    csv_file_path_players = 'Players.csv'
    
    if os.path.exists(csv_file_path_teams):
        df_teams = pd.read_csv(csv_file_path_teams)
        df_players = pd.read_csv(csv_file_path_players) if os.path.exists(csv_file_path_players) else pd.DataFrame()
        
        # Contar los jugadores para cada equipo
        player_counts = df_players.groupby('TeamID').size().rename('PlayerCount').reset_index()
        df_teams = df_teams.merge(player_counts, how='left', left_on='TeamID', right_on='TeamID')
        df_teams['PlayerCount'] = df_teams['PlayerCount'].fillna(0).astype(int)
        
        # Filtrar los equipos que pertenecen al usuario actual
        filtered_teams = df_teams[df_teams['UserID'] == current_user.id].to_dict(orient='records')
    else:
        filtered_teams = []
    
    return render_template('teams.html', user=current_user, teams=filtered_teams)


@views.route('/delete-team', methods=['POST'])
@login_required
def delete_team():
    team_id = request.json['teamId']
    csv_file_path = 'teams.csv'
    
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        # Filtrar para no incluir el equipo a borrar
        df = df[df['TeamID'] != team_id]
        df.to_csv(csv_file_path, index=False)  # Sobrescribe el archivo CSV sin el equipo borrado
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Archivo no encontrado'}), 404


@views.route('/calendar')
@login_required
def calendar():
    """Renderiza la plantilla 'calendar.html', pasando al usuario actual y la lista de partidos desde el CSV.

    Returns:
        str: La plantilla a renderizar.
    """
    csv_file_path = 'partidos.csv'  # Asegúrate de que esta ruta sea correcta
    matches = []

    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        matches = df[['match_date', 'tournament_name']].to_dict(orient='records')
    
    return render_template('calendar.html', user=current_user, matches=matches)


@views.route('/create-tournament', methods=['POST'])
@login_required
def create_tournament():
    """Crea un nuevo torneo y lo añade a la base de datos.

    Recupera los datos del torneo del formulario, verifica si
    todos los campos están completos, y luego añade el nuevo
    torneo a la base de datos.

    Returns:
        str: Redirige a la plantilla de torneos.
    """
    nombre = request.form.get('tournamentName')
    fecha_inicio = request.form.get('startDate')
    fecha_final = request.form.get('endDate')
    deporte = request.form.get('sport')
    equipos_participantes = request.form.get('teams')

    if not (nombre and fecha_inicio and fecha_final and deporte and equipos_participantes):
        flash('Todos los campos son requeridos.', 'error')
        return redirect(url_for('views.tournaments'))

    nuevo_torneo = Torneo(
        nombre=nombre,
        fecha_inicio=fecha_inicio,
        fecha_final=fecha_final,
        deporte=deporte,
        equipos_participantes=equipos_participantes,
        user_id=current_user.id
    )

    db.session.add(nuevo_torneo)
    db.session.commit()

    flash('Torneo creado con éxito.', 'success')
    return redirect(url_for('views.tournaments'))


@views.route('/get-tournaments')
@login_required
def get_tournaments():
    """Recupera y devuelve los torneos asociados al usuario
    actual en forma de JSON.

    Returns:
        dict: Lista de diccionarios con los datos de los torneos.
    """
    torneos = Torneo.query.filter_by(user_id=current_user.id).all()
    torneos_data = [{
        'id': torneo.id,
        'nombre': torneo.nombre,
        'fecha_inicio': torneo.fecha_inicio,
        'fecha_final': torneo.fecha_final,
        'deporte': torneo.deporte,
        'equipos_participantes': torneo.equipos_participantes,
    } for torneo in torneos]

    return jsonify(torneos_data)

@views.route('/create-team', methods=['POST'])
@login_required
def create_team():
    # Recuperar datos del formulario
    team_name = request.form.get('teamName')
    captain_name = request.form.get('captainName')
    captain_contact = request.form.get('captainContact')
    category = request.form.get('category')
    location = request.form.get('location')

    if not (team_name and captain_name and captain_contact and category and location):
        flash('Todos los campos son requeridos.', 'error')
        return redirect(url_for('views.teams'))

    # Leer el archivo CSV si existe
    csv_file_path = 'teams.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        if df.empty:
            team_id = 1
        else:
            max_team_id = df['TeamID'].apply(lambda x: int(x.split('-')[1])).max()
            team_id = max_team_id + 1
    else:
        # Crear un nuevo DataFrame si el archivo no existe
        df = pd.DataFrame(columns=['TeamID', 'UserID', 'TeamName', 'CaptainName', 'CaptainContact', 'Category', 'Location'])
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
    player_first_name = request.form.get('playerFirstName')
    player_last_name = request.form.get('playerLastName')
    player_age = request.form.get('playerAge')
    team_id = request.form.get('teamId')

    csv_file_path = 'Players.csv'
    player_id = generate_next_id(csv_file_path)

    player_data = {
        'PlayerID': player_id,
        'FirstName': player_first_name,
        'LastName': player_last_name,
        'Age': player_age,
        'TeamID': team_id
    }

    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        new_row = pd.DataFrame([player_data])
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = pd.DataFrame([player_data])

    df.to_csv(csv_file_path, index=False)
    flash('Jugador creado exitosamente', 'success')
    return redirect(url_for('views.teams'))


@views.route('/get-user-tournaments', methods=['GET'])
@login_required
def get_user_tournaments():
    torneos = Torneo.query.filter_by(user_id=current_user.id).all()
    torneos_data = [{'id': torneo.id, 'nombre': torneo.nombre} for torneo in torneos]
    return jsonify(torneos_data)


@views.route('/get-user-teams', methods=['GET'])
@login_required
def get_user_teams():
    """ Devuelve los equipos asociados al usuario actual en forma de JSON. """
    csv_file_path = 'teams.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        # Filtrar los equipos que pertenecen al usuario actual
        filtered_teams = df[df['UserID'] == current_user.id]
        teams_data = filtered_teams.to_dict(orient='records')
        teams_formatted = [{'id': team['TeamID'], 'name': team['TeamName']} for team in teams_data]
        return jsonify(teams_formatted)
    else:
        return jsonify([])  # Devuelve una lista vacía si no hay archivo o no hay equipos

    
@views.route('/schedule-match', methods=['POST'])
@login_required
def schedule_match():
    if request.method == 'POST':
        tournament_id = request.form.get('tournamentSelect')
        team_a = request.form.get('teamA')
        team_b = request.form.get('teamB')
        match_date = request.form.get('date')
        referee = request.form.get('referee')
        location = request.form.get('location')
        categoria = request.form.get('categoria')
        match_time = request.form.get('match_time')

        # Obtener el nombre del torneo basado en el ID
        torneo = Torneo.query.filter_by(id=tournament_id, user_id=current_user.id).first()
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

        df.to_csv(csv_file_path, index=False)

        flash('Partido programado con éxito!', 'success')
        return redirect(url_for('views.calendar'))
    return redirect(url_for('views.home'))
 

@views.route('/get-team-names', methods=['GET'])
def get_team_names():
    try:
        teams_df = pd.read_csv('teams.csv')
        teams = teams_df[['TeamID', 'TeamName']].to_dict(orient='records')
        return jsonify(teams)
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@views.route('/get-matches', methods=['GET'])
@login_required
def get_matches():
    try:
        matches_df = pd.read_csv('Partidos.csv')
        teams_df = pd.read_csv('teams.csv')
        
        # Filtrar los partidos para incluir solo los creados por el usuario actual
        matches_df = matches_df[matches_df['user_id'] == current_user.id]
        
        # Crear un diccionario para mapear TeamID a TeamName
        team_names = teams_df.set_index('TeamID')['TeamName'].to_dict()
        
        matches_df['team_a_name'] = matches_df['team_a'].map(team_names).fillna(matches_df['team_a'])
        matches_df['team_b_name'] = matches_df['team_b'].map(team_names).fillna(matches_df['team_b'])
        
        matches = matches_df.to_dict(orient='records')
        return jsonify(matches)
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@views.route('/get-teams/<categoria>')
@login_required
def get_teams(categoria):
    csv_file_path = 'teams.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        # Filtrar los equipos que pertenecen al usuario actual y la categoría especificada
        filtered_teams = df[(df['UserID'] == current_user.id) & (df['Category'] == categoria)]
        teams_data = filtered_teams.to_dict(orient='records')
        teams_formatted = [{'id': team['TeamID'], 'name': team['TeamName']} for team in teams_data]
        return jsonify(teams_formatted)
    else:
        return jsonify([])  # Devuelve una lista vacía si no hay archivo o no hay equipos

@views.route('/update-match', methods=['POST'])
@login_required
def update_match():
    data = request.get_json()
    
    csv_file_path = 'Partidos.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        
        match_id = data['match_id']
        match_index = df[df['match_id'] == match_id].index
        
        if not match_index.empty:
            match_index = match_index[0]
            df.at[match_index, 'team_a_score'] = data['team_a_score']
            df.at[match_index, 'team_b_score'] = data['team_b_score']
            df.at[match_index, 'faltas_team_a'] = data['faltas_team_a']
            df.at[match_index, 'faltas_team_b'] = data['faltas_team_b']
            
            df.to_csv(csv_file_path, index=False)
            return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Partido no encontrado'}), 404




@views.route('/get-tournament-info/<tournament_name>')
def get_tournament_info(tournament_name):
    partidos_csv_path = 'Partidos.csv'
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
        df_matches = df_matches[df_matches['tournament_name'] == tournament_name]

        # Reemplazar IDs de equipos por nombres
        df_matches['team_a'] = df_matches['team_a'].map(teams_dict)
        df_matches['team_b'] = df_matches['team_b'].map(teams_dict)

        # Calcular medias
        df_matches['media_puntuacion'] = df_matches[['team_a_score', 'team_b_score']].mean(axis=1)
        df_matches['media_faltas'] = df_matches[['faltas_team_a', 'faltas_team_b']].mean(axis=1)

        matches = df_matches.to_dict(orient='records')
    else:
        matches = []

    return jsonify(matches=matches)



def get_coordinates(address):
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'q': address, 'format': 'json'}
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; my bot/0.1; +http://mywebsite.com/bot)'}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Levanta una excepción para errores HTTP
        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
        else:
            print("No se encontraron resultados para la dirección proporcionada.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud HTTP: {e}")
        return None
    except ValueError as e:
        print(f"Error al decodificar la respuesta JSON: {e}")
        return None

def generate_map(address):
    coords = get_coordinates(address)
    if coords:
        lat, lon = coords
        point = Point(lon, lat)
        gdf = gpd.GeoDataFrame([{'geometry': point, 'address': address}])

        # Cargar directamente un archivo GeoJSON desde GitHub
        url = 'https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json'
        world = gpd.read_file(url)

        # Crear una caja delimitadora alrededor de las coordenadas
        buffer = 0.1  # Grados de latitud y longitud para la caja delimitadora
        bbox = box(lon-buffer, lat-buffer, lon+buffer, lat+buffer)

        # Filtrar el GeoDataFrame para incluir solo los países dentro de la caja delimitadora
        world = world[world.intersects(bbox)]

        ax = world.plot(figsize=(10, 6))
        gdf.plot(ax=ax, color='red', markersize=100)
        ax.set_title('Mapa con dirección geocodificada')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf8')
        buf.close()

        return image_base64
    else:
        print("No se pudieron obtener las coordenadas.")
        return None

@views.route('/get-map/<address>', methods=['GET'])
def get_map(address):
    map_image = generate_map(address)
    if map_image:
        return jsonify({'image_base64': map_image})
    else:
        return jsonify({'error': 'No se pudieron obtener las coordenadas.'}), 500




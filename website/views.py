# importacion de librerias necesarias
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Torneo, User, Team
from . import db
import json
import pandas as pd
import os
import uuid 
from datetime import date


views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    """Maneja la funcionalidad de la página de inicio.

    Si el método de la solicitud es POST, recupera la nota del formulario
    y verifica si es demasiado corta.
    Si no lo es, crea una nueva nota y la añade a la base de datos.
    Luego, muestra un mensaje de éxito
    y renderiza la plantilla "home.html".

    Si el método es GET, simplemente renderiza la plantilla "home.html".

    Returns:
        str: La plantilla a renderizar.
    """
    if request.method == 'POST':
        note = request.form.get('note')
        if len(note) < 1:
            flash('¡La nota es demasiado corta!', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('¡Nota añadida!', category='success')

    return render_template("home.html", user=current_user)


@views.route('/guest')
def guest():
    """Renderiza la plantilla "guest.html", pasando al usuario
    actual si está autenticado o None si no lo está.

    Returns:
        str: La plantilla a renderizar.
    """
    torneos = Torneo.query.all()

    return render_template("guest.html", user=current_user if current_user.is_authenticated else None, torneos=torneos)


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
        tournament_name = request.form.get('tournamentSelect')
        team_a = request.form.get('teamA')
        team_b = request.form.get('teamB')
        match_date = request.form.get('date')
        referee = request.form.get('referee')
        location = request.form.get('location')
        categoria = request.form.get('categoria')
        match_time = request.form.get('match_time') 

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
            'categoria': [categoria]
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
def get_matches():
    try:
        matches_df = pd.read_csv('Partidos.csv')
        teams_df = pd.read_csv('teams.csv')
        
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






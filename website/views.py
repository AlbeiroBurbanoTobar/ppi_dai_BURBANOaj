# importacion de librerias necesarias
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Torneo, User, Team

from . import db
import json
import pandas as pd
import os 

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
    """Renderiza la plantilla 'teams.html', pasando al usuario actual y los equipos desde el CSV."""
    # Ruta del archivo CSV
    csv_file_path = 'teams.csv'
    
    # Verificar si el archivo existe y leer los datos
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        teams_data = df.to_dict(orient='records')  # Convierte DataFrame a una lista de diccionarios
    else:
        teams_data = []
    
    return render_template('teams.html', user=current_user, teams=teams_data)


@views.route('/calendar')
@login_required
def calendar():
    """Renderiza la plantilla 'calendar.html', pasando al
    usuario actual.

    Returns:
        str: La plantilla a renderizar.
    """
    return render_template('calendar.html', user=current_user)


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

    # ID del usuario actual
    user_id = current_user.id

    # Leer el archivo CSV si existe
    csv_file_path = 'teams.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)

        # Filtrar los equipos del usuario actual para asignar un ID único
        user_teams = df[df['UserID'] == user_id]
        team_id = f"{user_id}-{len(user_teams) + 1}"
    else:
        # Crear un nuevo DataFrame si el archivo no existe
        df = pd.DataFrame(columns=['TeamID', 'UserID', 'TeamName', 'CaptainName', 'CaptainContact', 'Category', 'Location'])
        team_id = f"{user_id}-1"

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




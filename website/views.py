# importacion de librerias necesarias
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Torneo, User
from . import db
import json

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
    """Renderiza la plantilla 'teams.html', pasando al
    usuario actual.

    Returns:
        str: La plantilla a renderizar.
    """
    return render_template('teams.html', user=current_user)


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

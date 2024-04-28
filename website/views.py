from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note, Torneo, User
from . import db
import json

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    """
    Handles the home page functionality.

    If the request method is POST, it retrieves the note from the form, checks if it is too short,
    and if not, it creates a new note and adds it to the database. It then flashes a success
    message and renders the home.html template.

    If the request method is GET, it simply renders the home.html template.
    """
    if request.method == 'POST':
        note = request.form.get('note')  # Gets the note from the HTML
        if len(note) < 1:
            flash('Note is too short!', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)  # Providing the schema for the note
            db.session.add(new_note)  # Adding the note to the database
            db.session.commit()
            flash('Note added!', category='success')
    return render_template("home.html", user=current_user)

@views.route('/guest')
def guest():
    """
    Renders the guest.html template, passing the current user if authenticated,
    or None if there is no authenticated user.
    """
    # Assuming you want to pass the user information if authenticated,
    # or None if there is no authenticated user.

    torneos = Torneo.query.all()  # Recupera todos los torneos
    
    return render_template("guest.html", user=current_user if current_user.is_authenticated else None, torneos = torneos)

@views.route('/delete-note', methods=['POST'])
def delete_note():
    """
    Deletes a note from the database.

    This function expects a JSON object from the INDEX.js file, with a 'noteId'
    property. It then retrieves the note with the given ID, and if the note
    belongs to the current user, it deletes the note from the database.
    """
    note = json.loads(request.data)  # this function expects a JSON from the INDEX.js file
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()
    return jsonify({})
@views.route('/tournaments')
@login_required
def tournaments():
    return render_template('tournaments.html', user=current_user)

@views.route('/teams')
@login_required
def teams():
    return render_template('teams.html', user=current_user)

@views.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html', user=current_user)

@views.route('/create-tournament', methods=['POST'])
@login_required
def create_tournament():
    nombre = request.form.get('tournamentName')
    fecha_inicio = request.form.get('startDate')
    fecha_final = request.form.get('endDate')
    deporte = request.form.get('sport')
    equipos_participantes = request.form.get('teams')
    
    if not nombre or not fecha_inicio or not fecha_final or not deporte or not equipos_participantes:
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
    torneos = Torneo.query.filter_by(user_id=current_user.id).all()
    torneos_data = []
    for torneo in torneos:
        torneos_data.append({
            'id': torneo.id,
            'nombre': torneo.nombre,
            'fecha_inicio': torneo.fecha_inicio,
            'fecha_final': torneo.fecha_final,
            'deporte': torneo.deporte,
            'equipos_participantes': torneo.equipos_participantes,
            # Añade aquí más campos si es necesario
        })
    return jsonify(torneos_data)



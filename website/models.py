# importacion de librerias necesarias
from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class Note(db.Model):
    """Representa una nota en la aplicación.

    Atributos:
        id (db.Integer): Identificador único de la nota.
        data (db.String(10000)): Contenido de la nota.
        date (db.DateTime): Fecha y hora en que se creó la nota.
        user_id (db.Integer): Identificador del usuario que creó la nota.
    """
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(db.Model, UserMixin):
    """Representa un usuario de la aplicación.

    Atributos:
        id (db.Integer): Identificador único del usuario.
        email (db.String(150)): Dirección de correo electrónico del usuario.
        password (db.String(150)): Contraseña cifrada del usuario.
        first_name (db.String(150)): Nombre del usuario.
        notes (db.relationship('Note')): Notas asociadas al usuario.
        torneos (db.relationship('Torneo')): Torneos asociados al usuario.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    notes = db.relationship('Note')
    torneos = db.relationship('Torneo', back_populates='creador')


class Torneo(db.Model):
    """Representa un torneo en la aplicación.

    Atributos:
        id (db.Integer): Identificador único del torneo.
        nombre (db.String(150)): Nombre del torneo.
        fecha_inicio (db.String(50)): Fecha de inicio del torneo.
        fecha_final (db.String(50)): Fecha de finalización del torneo.
        deporte (db.String(50)): Deporte asociado al torneo.
        equipos_participantes (db.Integer): Número de equipos participantes.
        user_id (db.Integer): Identificador del usuario que creó el torneo.
        creador (db.relationship('User')): Relación inversa para acceder a los torneos desde el usuario.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    fecha_inicio = db.Column(db.String(50), nullable=False)
    fecha_final = db.Column(db.String(50), nullable=False)
    deporte = db.Column(db.String(50), nullable=False)
    equipos_participantes = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relación inversa para acceder a los torneos desde el usuario
    creador = db.relationship('User', back_populates='torneos')

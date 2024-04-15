from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class Note(db.Model):
    """
    Represents a note in the application.

    Attributes:
        id (db.Integer): The unique identifier of the note.
        data (db.String(10000)): The content of the note.
        date (db.DateTime(timezone=True)): The date and time when the note was created.
        user_id (db.Integer): The identifier of the user who created the note.
    """
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class User(db.Model, UserMixin):
    """
    Represents a user of the application.

    Attributes:
        id (db.Integer): The unique identifier of the user.
        email (db.String(150)): The email address of the user.
        password (db.String(150)): The hashed password of the user.
        first_name (db.String(150)): The first name of the user.
        notes (db.relationship('Note')): The notes associated with the user.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    notes = db.relationship('Note')

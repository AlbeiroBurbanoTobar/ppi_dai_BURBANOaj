# importacion de librerias necesarias
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager

# Instancia de la base de datos (global para conveniencia en este ejemplo)
db = SQLAlchemy()

# Constante con el nombre de la base de datos
DB_NAME = "database.db"


def create_app():
    """Crea una instancia de la aplicación Flask con configuración de la base de datos.

    Retorna:
        Flask: Una aplicación Flask configurada.
    """
    app = Flask(__name__)

    # Clave secreta para la gestión de sesiones 
    # (reemplazar con un valor fuerte y aleatorio)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'

    # Configuración de la URI de la base de datos
    # (considera usar variables de entorno para mayor seguridad)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    # Inicializar SQLAlchemy con la aplicación
    db.init_app(app)

    # Importar blueprints de los módulos views y auth
    from .views import views
    from .auth import auth

    # Registrar los blueprints con prefijos de URL
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # Importar modelos 
    # asumiendo que User y Note están definidos en otro lugar)
    from .models import User, Note

    # Crear tablas de la base de datos si no existen
    # (dentro del contexto de la aplicación)
    with app.app_context():
        db.create_all()

    # Configurar LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'views.guest'
    login_manager.init_app(app)

    # Función para cargar el usuario para el LoginManager
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    """Crea la base de datos si no existe.

    Args:
        app (Flask): La instancia de la aplicación Flask.
    """
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('¡Base de datos creada!')

# importacion de librerias necesarias
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
# Importación de la instancia de la base de datos desde __init__.py
from . import db  

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja la funcionalidad de inicio de sesión.

    Si el método de la solicitud es POST, recupera el correo electrónico
    y la contraseña del formulario, verifica si el usuario existe y si la
    contraseña es correcta. Si el inicio de sesión es exitoso, el usuario
    es redirigido a la página de inicio. De lo contrario, se muestran
    mensajes de error apropiados.

    Si el método es GET, simplemente renderiza la plantilla de inicio de sesión.

    Returns:
        str: La plantilla a renderizar.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                flash('¡El inicio de sesión fue un éxito!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Contraseña incorrecta, inténtalo de nuevo.', category='error')
        else:
            flash('El correo electrónico no existe.', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario actual y lo redirige a la página de invitado.

    Returns:
        str: La plantilla a renderizar.
    """
    logout_user()
    return redirect(url_for('views.guest'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    """Maneja la funcionalidad de registro de nuevos usuarios.

    Si el método de la solicitud es POST, recupera el correo electrónico,
    nombre y contraseñas del formulario.
    Verifica si el correo electrónico ya existe, si el correo electrónico
    y la contraseña cumplen con los requisitos mínimos de longitud y si
    las contraseñas coinciden. Si todas las validaciones son exitosas,
    crea un nuevo usuario y lo agrega a la base de datos.
    Luego inicia sesión al usuario y lo redirige a la página de inicio.

    Si el método es GET, simplemente renderiza la plantilla de registro.

    Returns:
        str: La plantilla a renderizar.
    """
    if not session.get('accepted_privacy_policy', False):
        return redirect(url_for('auth.privacy_policy'))

    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()

        if user:
            flash('El correo electrónico ya existe.', category='error')
        elif len(email) < 4:
            flash('El correo electrónico debe tener más de 3 caracteres.',
                  category='error')
        elif len(first_name) < 2:
            flash('El nombre debe tener más de 1 carácter.', category='error')
        elif password1 != password2:
            flash('Las contraseñas no coinciden.', category='error')
        elif len(password1) < 7:
            flash('La contraseña debe tener al menos 7 caracteres.', category='error')
        else:
            new_user = User(email=email, first_name=first_name,
                            password=generate_password_hash(password1))
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user, remember=True)
            flash('¡Cuenta creada!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Maneja la funcionalidad de cambio de contraseña.

    Si el método de la solicitud es POST, recupera la contraseña actual,
    la nueva contraseña y la confirmación de la nueva contraseña del
    formulario. Verifica si la contraseña actual es correcta, si la
    nueva coincide con la confirmación y si cumple con el requisito
    de longitud mínima. Si todas las validaciones son exitosas, actualiza la
    contraseña del usuario en la base de datos.

    Returns:
        str: La plantilla a renderizar.
    """
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        user = current_user

        if not check_password_hash(user.password, current_password):
            flash('La contraseña actual es incorrecta.', category='error')
        elif new_password != confirm_password:
            flash('Las contraseñas no coinciden.', category='error')
        elif len(new_password) < 7:
            flash('La contraseña debe tener al menos 7 caracteres.', category='error')
        else:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash('¡Tu contraseña ha sido actualizada!', category='success')
            return redirect(url_for('views.home'))

    return render_template("change_password.html", user=current_user)


@auth.route('/privacy-policy', methods=['GET', 'POST'])
def privacy_policy():
    """Muestra la política de privacidad y maneja su aceptación.

    Si el método de la solicitud es POST y se acepta la política
    de privacidad, configura la sesión para recordar la aceptación
    y redirige al usuario a la página de registro.

    Returns:
        str: La plantilla a renderizar.
    """
    if request.method == 'POST':
        if 'accept' in request.form:
            session['accepted_privacy_policy'] = True
            return redirect(url_for('auth.sign_up'))
        else:
            return redirect(url_for('views.guest'))

    return render_template("privacy_policy.html", user=current_user)

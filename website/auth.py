from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  # means from __init__.py import db
from flask_login import login_user, login_required, logout_user, current_user
from flask import session
from flask_login import current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles the login functionality.

    If the request method is POST, it retrieves the email and password from the form,
    checks if the user exists, and if the password is correct. If the login is successful,
    the user is redirected to the home page. Otherwise, appropriate error messages are flashed.

    If the request method is GET, it renders the login template.
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
    """
    Logs out the current user and redirects them to the login page.
    """
    logout_user()
    return redirect(url_for('views.guest'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    """
    Handles the sign-up functionality.

    If the request method is POST, it retrieves the email, first name, and passwords from the form.
    It checks if the email already exists, if the email and password meet the minimum length requirements,
    and if the passwords match. If all the validations pass, a new user is created and added to the database.
    The user is then logged in and redirected to the home page.

    If the request method is GET, it renders the sign-up template.
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
            flash('Email ya existe.', category='error')
        elif len(email) < 4:
            flash('El correo electrónico debe tener más de 3 caracteres.', category='error')
        elif len(first_name) < 2:
            flash('El nombre debe tener más de 1 carácter.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('La contraseña debe tener al menos 7 caracteres.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('¡Cuenta creada!', category='success')
            return redirect(url_for('views.home'))
    return render_template("sign_up.html", user=current_user)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        user = current_user
        if not check_password_hash(user.password, current_password):
            flash('La contraseña actual es incorrecta.', category='error')
        elif new_password != confirm_password:
            flash('Las contraseñas no coinciden', category='error')
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
    if request.method == 'POST':
        if 'accept' in request.form:
            # Si se acepta, configuramos la sesión para recordar la aceptación
            session['accepted_privacy_policy'] = True
            # Luego redirigimos a la página de registro
            return redirect(url_for('auth.sign_up'))
        else:
            # Si no se acepta, o si se presiona 'decline', redirigimos a guest
            return redirect(url_for('views.guest'))
    # Si es un método GET, simplemente mostramos la política de privacidad
    return render_template("privacy_policy.html", user=current_user)

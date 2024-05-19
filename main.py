import os
from website import create_app
from flask import redirect, url_for

app = create_app()

@app.route('/')
def default():
    return redirect(url_for('views.guest'))

if __name__ == '__main__':
    """
    Runs the Flask application.
    This code is executed when the script is run directly (not imported as a module).
    It creates a Flask application instance using the create_app() function from the
    'website' module, and then runs the application.
    """
    port = int(os.environ.get("PORT", 5000))  # Obtén el puerto de la variable de entorno PORT o usa 5000 por defecto
    app.run(debug=True, host='0.0.0.0', port=port)  # Ejecuta la aplicación en el puerto especificado

from website import create_app

app = create_app()

if __name__ == '__main__':
    """
    Runs the Flask application in debug mode.

    This code is executed when the script is run directly (not imported as a module).
    It creates a Flask application instance using the create_app() function from the
    'website' module, and then runs the application in debug mode.
    """
    @app.route('/')
    def default():
        return redirect(url_for('views.guest'))
    app.run(debug=True, host='0.0.0.0')
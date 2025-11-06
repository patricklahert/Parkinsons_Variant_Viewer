from flask import Flask
from .db import close_db

def create_app():
    app = Flask(__name__)
    app.config['DATABASE'] = 'instance/parkinsons.db'

    # Import and register routes
    from .routes import bp
    app.register_blueprint(bp)

    # Close DB connection on teardown
    app.teardown_appcontext(close_db)

    return app

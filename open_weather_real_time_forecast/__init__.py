from flask import Flask
from config import Config

app = Flask(__name__, instance_relative_config=False)

def create_app():
    app.config.from_object(Config)

    from .routes import api

    app.register_blueprint(api.api_bp)

    # Import Dash application
    from .dashboard import create_dashboard
    dash = create_dashboard(app)

    return dash

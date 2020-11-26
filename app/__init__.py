from flask import Flask
from flask_migrate import Migrate

from config import Config
from .database import db
from .constants import MIGRATION_ENV

app = Flask(__name__, instance_relative_config=False)

def create_app(env=None):
    app.config.from_object(Config)

    db.init_app(app)
    db.app = app
    migrate = Migrate(app, db)

    if env == MIGRATION_ENV:
        return app

    from .routes import api

    app.register_blueprint(api.api_bp)

    from .dashboard import create_dashboard
    dash = create_dashboard(app)

    return dash

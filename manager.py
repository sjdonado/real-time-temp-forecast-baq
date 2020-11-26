from flask_script import Manager
from flask_migrate import MigrateCommand

from app import create_app
from app.constants import MIGRATION_ENV

app = create_app(env=MIGRATION_ENV)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
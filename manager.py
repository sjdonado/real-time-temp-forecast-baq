from flask_script import Manager
from flask_migrate import MigrateCommand

from open_weather_real_time_forecast import create_app
from open_weather_real_time_forecast.constants import MIGRATION_ENV

app = create_app(env=MIGRATION_ENV)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
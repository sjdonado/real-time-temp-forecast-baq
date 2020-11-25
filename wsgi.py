import os

from open_weather_real_time_forecast import create_app

PORT = int(os.environ.get("PORT", 5000))
DEBUG = int(os.environ.get("DEBUG", True))

app = create_app()

if __name__ == "__main__":
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
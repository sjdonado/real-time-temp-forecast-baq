## Setup

1. create virtualenv `python3 -m venv local-env`
2. activate virtualenv `source local-env/bin/activate .`
3. install dependencies `pip install -r requirements.txt`
4. run `python manager.py db upgrade`
5. run `python wsgi.py`
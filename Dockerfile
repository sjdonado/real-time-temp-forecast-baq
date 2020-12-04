FROM python:3.8.3

WORKDIR /usr/src/app

RUN pip install gunicorn

COPY ./requirements.txt .
RUN pip3 install  -r requirements.txt

COPY . .

CMD gunicorn -w 2 --bind 0.0.0.0:$PORT wsgi:app
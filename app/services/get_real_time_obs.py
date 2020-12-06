import os
import re

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

from datetime import date, datetime, timedelta

from urllib.request import urlopen
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

from threading import Thread 

from metar import Metar

import keras
import joblib
from sklearn.preprocessing import MinMaxScaler
from keras.utils import data_utils

from app.database import db, Report, ModelData
from app.services.s3 import get_file, upload_file

model = None
scaler = None

TMP_DIR = f"{os.path.abspath(os.getcwd())}/tmp"

# Fetch Observations

def fetch(url):
    try:
        html = urlopen(url).read()
        soup = BeautifulSoup(html, features='html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        return soup
    except Exception:
        return None


def get_last_cortissoz_metars(date):
    now = datetime.utcnow()
    url = f"https://www.ogimet.com/display_metars2.php?lang=en&lugar=SKBQ&tipo=SA&ord=DIR&nil=NO&fmt=txt&ano={date.year}&mes={date.month}&day={date.day}&hora={date.hour-5}&min=00&anof={now.year}&mesf={now.month}&dayf={now.day}&horaf={now.hour}&minf=59"
    soup = fetch(url)
    if soup is None:
        return []
    text = soup.get_text()
    if f"No hay METAR/SPECI de SKBQ en el periodo solicitado" in text:
        return []
    data = []
    text = re.sub('\s\s+', ' ', text)
    matches = re.findall(r"\s(\d+)[\s]METAR\s(.*)=", text)
    for match in matches:
        if ',' not in match:
            data.append(match)
    return data

# Parse data from METAR
def get_temperature(obs):
    """ returns temp K """
    return float(re.findall(r".*temperature:\s(.*)[\s]C\s*", obs)[0]) + 273.15


def parse_metars(metars):
    df = []
    for metar in metars:
        try:
            temp = 0.0
            obs = Metar.Metar(metar[1]).string()
            temp = get_temperature(obs)
            df.append([datetime.strptime(metar[0], '%Y%m%d%H%M'), temp])
        except Exception as e:
            error = e
            # print('error:', e)

    df = pd.DataFrame(df,columns=['date', 'air'])
    df['date'] = df['date'].apply(lambda x: x.replace(minute=0, second=0))
    df = df.drop_duplicates(subset='date')
    df = df.reset_index(drop=True)
    df = df.sort_values(by='date')
    return df


# Model helpers
def create_dataset(dataset, time_steps):
    '''Function to create a dataset to feed into an LSTM. Returns X, Y'''
    X, Y = [], []
    for i in range(dataset.shape[0] - time_steps):
        X.append(dataset[i:(i + time_steps), 0])
        Y.append(dataset[i + time_steps, 0])
    return np.array(X), np.array(Y)


def job():
    try:
        now = datetime.utcnow()
        metars = get_last_cortissoz_metars(now)
        last_data_df = parse_metars(metars)
        print('[job]: last metars fetched', last_data_df.shape)

        boundary = (datetime.today() - timedelta(hours=5))

        # Fix unreported observations using the model
        now = datetime.utcnow()
        metars = get_last_cortissoz_metars(now)
        last_data_df = parse_metars(metars)

        boundary = (datetime.today() - timedelta(hours=4))

        while True:
            for idx, row in last_data_df.iterrows():
                expected = boundary + timedelta(hours=idx)
                if row.date.hour != expected.hour:
                    if idx < 4:
                        metars = get_last_cortissoz_metars(expected)
                        last_data_df = parse_metars(metars)
                        boundary -= timedelta(hours=5)
                    else:
                        data = last_data_df[idx-4:idx]['air'].values.reshape(-1,1)
                        data = scaler.transform(data)
                        y_score = model.predict(np.reshape(data, (1, 4, 1)))
                        y_score = scaler.inverse_transform(y_score)
                        last_data_df = last_data_df.append({'date': expected, 'air': y_score[0][0] }, ignore_index=True)
                        last_data_df = last_data_df.sort_values(by='date')
                        last_data_df = last_data_df.reset_index(drop=True)
                    break

            if idx == last_data_df.shape[0] - 1:
                break

        print('[job]: data fixed', last_data_df.shape)

        last_data_df = last_data_df.tail(5)

        # Normalization
        test_data = last_data_df['air'].values.reshape(-1,1)
        test_data = scaler.transform(test_data)

        # Fit last observation
        time_steps = 4
        X_test, y_test = create_dataset(test_data, time_steps)

        X_test = np.reshape(X_test, (X_test.shape[0], time_steps, 1))
        model.fit(X_test, y_test, batch_size=4)

        # Forecast
        X_last_data = np.reshape(test_data[1:5], (1, time_steps, 1))
        y_score = model.predict(X_last_data)
        y_score = scaler.inverse_transform(y_score)

        report = db.session.query(Report).filter(Report.active == True)
        last_reports = db.session.query(Report).filter(Report.active == False).count()

        filename = f"{datetime.utcnow().strftime('%Y%m%d%H')}.csv"
        tmp_path = f"{TMP_DIR}/{filename}"

        last_data_df.to_csv(tmp_path, index=False)
        path = upload_file('reports', filename, tmp_path)

        if last_reports > 0 and last_reports % 5 == 0:
            filename = 'model.h5'
            tmp_path = f"{TMP_DIR}/{filename}"

            model.save(path)
            upload_file('data', filename, tmp_path)

        forecast = float(y_score[0][0])

        report.update({"active": False, "forecast": forecast, "path": path})
        db.session.commit()

        print('[job]: data saved', forecast, path)
    except Exception as e:
        print(e)


def run():
    global model
    global scaler

    if model is None or scaler is None:
        keras_model_db = db.session.query(ModelData).filter(ModelData.path == 'data/model.h5').first()
        model_file = data_utils.get_file('model.h5', get_file(keras_model_db))
        model = keras.models.load_model(model_file)

        scaler__db = db.session.query(ModelData).filter(ModelData.path == 'data/scaler.save').first()
        scaler_file = data_utils.get_file('scaler.save', get_file(scaler__db))
        scaler = joblib.load(scaler_file)

    delay = datetime.now() - timedelta(minutes=55)
    active_report = db.session.query(Report).filter((Report.active == True) | (Report.created > delay)).first()
    if active_report is not None:
        return 'skipped', active_report

    report = Report()
    db.session.add(report)
    db.session.commit()

    Thread(target=job, daemon=True).start()

    return 'sent', report
    
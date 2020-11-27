import os
import re

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

from app.database import db, Report

BASE_DIR = f"{os.path.abspath(os.getcwd())}/app"

model = keras.models.load_model(f"{BASE_DIR}/data/model.h5")
scaler = joblib.load(f"{BASE_DIR}/data/scaler.save")

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


def get_last_cortissoz_metars():
    now = datetime.utcnow()
    url = f"https://www.ogimet.com/display_metars2.php?lang=en&lugar=SKBQ&tipo=SA&ord=DIR&nil=NO&fmt=txt&ano={now.year}&mes={now.month}&day={now.day}&hora={now.hour-10}&min=00&anof={now.year}&mesf={now.month}&dayf={now.day}&horaf={now.hour}&minf=59"
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

# Model helpers
def create_dataset(dataset, time_steps):
    '''Function to create a dataset to feed into an LSTM. Returns X, Y'''
    X, Y = [], []
    for i in range(dataset.shape[0] - time_steps):
        X.append(dataset[i:(i + time_steps), 0])
        Y.append(dataset[i + time_steps, 0])
    return np.array(X), np.array(Y)

def job():
    metars = get_last_cortissoz_metars()
    print('[job]: last metars fetched')

    last_data_df = []
    for metar in metars:
        try:
            temp = 0.0
            obs = Metar.Metar(metar[1]).string()
            temp = get_temperature(obs)
            last_data_df.append([datetime.strptime(metar[0], '%Y%m%d%H%M'), temp])
        except Exception as e:
            print('error:', e)
        
    print('[job]: metars parsed')

    last_data_df = pd.DataFrame(last_data_df,columns=['date', 'air']).tail(5)

    # Evaluate
    last_data_df['date'] = pd.to_datetime(last_data_df.date)
    last_data_df = last_data_df.sort_values(by='date')

    # Sort by date
    last_data_df['date'] = pd.to_datetime(last_data_df.date)
    last_data_df = last_data_df.sort_values(by='date')

    # Normalization
    test_data = last_data_df['air'].values.reshape(-1,1)
    test_data = scaler.transform(test_data)

    # Fit last observation
    time_steps = 4
    X_test, y_test = create_dataset(test_data, time_steps)

    X_test = np.reshape(X_test, (X_test.shape[0], time_steps, 1))
    model.fit(X_test, y_test, batch_size=4)

    X_last_data = np.reshape(test_data[1:5], (1, time_steps, 1))

    y_score = model.predict(X_last_data)
    y_score = scaler.inverse_transform(y_score)

    report = db.session.query(Report).filter(Report.active == True)
    last_reports = db.session.query(Report).filter(Report.active == False).count()

    path = None
    if last_reports % 5 == 0:
        path = f"{BASE_DIR}/blob/{datetime.utcnow().strftime('%Y%m%d%H')}.csv"
        last_data_df.to_csv(path, index=False)
        model.save((f"{BASE_DIR}/data/model.h5"))

    report.update({"active": False, "prediction": y_score[0][0], "path": path})
    db.session.commit()

    print('[job]: data saved')


def run():
    one_hour_ago = datetime.now() - timedelta(hours=1)
    active_report = db.session.query(Report).filter((Report.active == True) | (Report.created >= one_hour_ago)).first()
    if active_report is not None:
        return 'skipped', active_report

    report = Report()
    db.session.add(report)
    db.session.commit()

    Thread(target=job, daemon=True).start()

    return 'sent', report
    
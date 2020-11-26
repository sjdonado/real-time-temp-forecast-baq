import os
import re
import shutil

import portolan
import multiprocessing
from datetime import date, timedelta, datetime
from calendar import monthrange

from urllib.request import urlopen
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

from threading import Thread 

from metar import Metar

from app.database import db, Report

BASE_DIR = f"{os.path.abspath(os.getcwd())}/open_weather_real_time_forecast"

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

def get_stations_noaa():
    soup = fetch('https://tgftp.nws.noaa.gov/data/observations/metar/stations/')
    stations = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if 'TXT' in href:
            stations.append(href.split('.TXT')[0])
    return stations

def get_stations_with_coords():
    soup = fetch('http://weather.rap.ucar.edu/surface/stations.txt')
    text = soup.get_text()
    matches = re.findall(r".*([A-Z]{4}).*[\s]([\d]+\s[\d]+\w).*[\s]([\d]+\s[\d]+\w)[\s]*(\d{1,4}).*", text)
    stations = []
    for match in matches:
        stations.append({'ICAO': match[0], 'coords': "+".join(match[1:]).replace(' ', '-')})
    return stations

def gms_to_lat_lng(gms):
    comp = gms.split('-')
    if len(comp)==2:
        if 'N' in comp[1] or 'E' in comp[1]:
            return int(comp[0])+(int(comp[1][:len(comp)])/60)
        else:
            return -(int(comp[0])+(int(comp[1][:len(comp)])/60))
    elif len(comp)==3:
        if 'N' in comp[2] or 'E' in comp[2]:
            return int(comp[0])+(int(comp[1][:len(comp)])/60)+(int(comp[2][:len(comp)-1])/60)
        else:
            comp[2]='0'+comp[2][:len(comp)-1]
            return (-int(comp[0])-(int(comp[1][:len(comp)])/60)-(int(comp[2][:len(comp)-1])/3600))
    else:
        return 0

def get_last_metar(station):
    now = datetime.utcnow()
    soup = fetch(f"https://www.ogimet.com/display_metars2.php?lugar={station['ICAO']}&tipo=SA&ord=DIR&nil=NO&fmt=text&ano={now.year}&mes={now.month}&day={now.day}&hora={now.hour}")
    if soup is None:
        return []
    text = soup.get_text()
    if f"No hay METAR/SPECI de {station} en el periodo solicitado" in text:
        return []
    data = []
    text = re.sub('\s\s+', ' ', text)
    matches = re.findall(r"\s(\d+)[\s]METAR\s(.*)=", text)
    for match in matches:
        if ',' not in match:
            (lat, lng, elev) = station['coords'].split('+')
            data.append({ 'lat': gms_to_lat_lng(lat), 'lng': gms_to_lat_lng(lng), 'elev': elev, 'datetime': match[0], 'observation': match[1] })
    return data

# Parse data from METAR

PRESSURE_LEVELS_HEIGHTS_VALUES = [
    762,
    1458,
    3013,
    5576,
    9166,
    11787,
    16000,
]

def get_pressure(obs):
    """returns press Pa
    
    format examples:
        pressure: 1027.8 mb
        3-hr pressure change 1.7hPa, increasing, then decreasing
    """

    press = 0.0
    if 'pressure:' in obs:
        press = float(re.findall(r".*pressure:\s(.*)[\s]mb\s*", obs)[0])
    else:
        press = float(re.findall(r".*pressure[\s]change[\s](.*)hPa", obs)[0])

    return press * 100

def get_dew_point(obs):
    """ returns temp K """
    return float(re.findall(r".*dew[\s]point:\s(.*)[\s]C\s*", obs)[0]) + 273.15

def get_temperature(obs):
    """ returns temp K """
    return float(re.findall(r".*temperature:\s(.*)[\s]C\s*", obs)[0]) + 273.15

def nearest_neighbour(X_lng, Y_lat, lng, lat):
    diff_x = 100
    diff_y = 100
    pos_x = 0
    pos_y = 0
    for x in X_lng:
        diff = abs(x - lng)
        if diff_x > diff:
            pos_x = x
            diff_x = diff

    for y in Y_lat:
        diff = abs(y - lat)
        if diff_y > diff:
            pos_y = y
            diff_y = diff
    return (pos_x, pos_y)

def get_wind_comps(obs):
    # ESE at 11 knots
    # WSW at greater than 99 knots
    if 'knots' in obs and 'variable' not in obs:
        compass_point, mag = re.findall(r".*wind:\s(\w+)[\s|\w]*[\s]([0-9]+)[\s]knots", obs)[0]
        ang = portolan.middle(compass_point)
        # print(f"get_wind_comps, compass_point:{compass_point} mag:{mag}\n")
        mag = int(mag) / 1.944
        u = mag * np.sin(ang)
        v = mag * np.cos(ang)
        return (u, v)
    else:
        return (0, 0)

def elev_to_press_level(elev):
    max_diff = 10000
    level = 0
    for (idx, val) in enumerate(PRESSURE_LEVELS_HEIGHTS_VALUES):
        diff = abs(val - elev)
        if max_diff > diff:
            level = idx
            max_diff = diff
    return level

# Physical formulas

def vapor_pressure(T):
    """Return partial water vapor pressure (e) or saturation vapor pressure (es) hPa.
    
    dew_point for (e) K
    temperature for (es) K
    more info: https://cran.r-project.org/web/packages/humidity/vignettes/humidity-measures.html
    alternatives: August–Roche–Magnus formula
    """
    a = 17.2693882
    b = 35.86
    e = 6.1078 * np.exp(a * (T - 273.16) / (T - b))
    
    return e

def calculate_shum(dew_point, pressure):
    """Return specific humidity kg/kg.
    
    dew_point K
    pressure  Pa
    more info: https://cran.r-project.org/web/packages/humidity/vignettes/humidity-measures.html
    """
    e = vapor_pressure(dew_point)
    q = 0.622 * e  / (pressure - 0.378 * e)
    
    #print(dew_point, pressure, q)    
    return q

def calculate_rhum(dew_point, temp):
    """ validator: https://www.wpc.ncep.noaa.gov/html/dewrh.shtml """
    rhum = 100 * vapor_pressure(dew_point) / vapor_pressure(temp)

    #print(dew_point, temp, rhum)
    return rhum

# Helper functions

def fetch_last_metars(station):
    localdata = []
    metar_obs = get_last_metar(station)
    for obs_item in metar_obs:
        hour = datetime.strptime(obs_item['datetime'], '%Y%m%d%H%M').hour
        localdata.append([obs_item['lat'], obs_item['lng'], obs_item['elev'], obs_item['datetime'], obs_item['observation']])
    return localdata


def job():
    global parse_metars

    noaa_stations = get_stations_with_coords()
    print('[job]: noaa stations fetched')

    # Fetch last metars
    jobs = multiprocessing.cpu_count()
    with multiprocessing.Pool(jobs - 1) as p:
        data = p.map(fetch_last_metars, noaa_stations)
        
    df = []
    for elem in data:
        for arr in elem:
            df.append(arr)

    print('[job]: last metars fetched')

    df = pd.DataFrame(data=df, columns=['lat', 'lng', 'elev', 'datetime', 'observation'])

    df['datetime'] = pd.to_datetime(df.datetime)
    df = df.sort_values(by='datetime')  

    def parse_metars(idx):
        dt = []
        cords = []
        row = df.iloc[idx]
        try:
            temp = 0.0
            obs = Metar.Metar(row['observation']).string()
            if ('temperature' in obs):
                temp = get_temperature(obs)
                if temp < 331.15:
                    dt.append([row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), row['lat'], row['lng'], row['elev'], 'air', temp])

            (u, v) = get_wind_comps(obs)
            if (u, v) != (0,0):
                dt.append([row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), row['lat'], row['lng'], row['elev'], 'uwnd', u])
                dt.append([row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), row['lat'], row['lng'], row['elev'], 'vwnd', v])

            if ('pressure' in obs):
                press = get_pressure(obs)
                if press < 105100 and press > 52200:
                    dt.append([row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), row['lat'], row['lng'], row['elev'], 'press', press])

            if ('dew point' in obs and 'pressure' in obs):
                dew_point = get_dew_point(obs)
                if dew_point > 0 and press < 105100 and press > 52200 and dew_point <= temp and temp != 0 :
                    shum = calculate_shum(dew_point, press)
                    rhum = calculate_rhum(dew_point, temp)
                    dt.append([row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), row['lat'], row['lng'], row['elev'], 'rhum', rhum])
                    if shum < 0.05:
                        dt.append([row['datetime'].strftime("%Y-%m-%d %H:%M:%S"), row['lat'], row['lng'], row['elev'], 'shum', shum])

            cords.append((row['lat'], row['lng']))
        except Exception as e:
            str_err = str(e)
            if 'Unparsed groups' not in str_err and '_handleTime' not in str_err and '_handleWind' not in str_err and "NSW" not in str_err:
                print('index:', idx, 'error:', e)
        return (dt, cords)

    # Parse metars
    jobs = multiprocessing.cpu_count()
    with multiprocessing.Pool(jobs - 1) as p:
        data = p.map(parse_metars, range(len(df)))
        
    df_parsed_metars = []
    active_stations = []
    for elem in data:
        df_parsed_metars += elem[0]
        for cords in elem[1]:
            if (cords not in active_stations):
                active_stations.append(cords)

    print('[job]: metars parsed')

    df_metar_info = pd.DataFrame(df_parsed_metars,columns=['datetime','lat','lng','elev','variable','value'])

    report = db.session.query(Report).filter(Report.active == True)
    df_metar_info.to_csv(report[0].path, index=False)

    report.update({"active": False})
    print('[job]: data saved')


def run():
    active_reports = db.session.query(Report).filter(Report.active == True).count()
    if active_reports > 0:
        return True

    report = Report()
    report.path = f"{BASE_DIR}/blob/{datetime.utcnow().strftime('%Y%m%d%H')}.csv"
    db.session.add(report)
    db.session.commit()

    Thread(target=job, daemon=True).start()

    return False
    
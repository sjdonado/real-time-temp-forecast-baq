import os
import datetime

import dash
import plotly.express as px
import dash_core_components as dcc
import dash_html_components as html

from plotly.subplots import make_subplots

import pandas as pd

from app.database import db, Report
from app.services.s3 import get_file

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


def create_dashboard(server):
    title = 'Realtime temperature forecast'

    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/dashboard/',
        external_stylesheets=external_stylesheets,
        title=title
    )

    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ], id='body')

    def build_index_page():
        children = [
            html.H1(children=title),
        ]

        last_report = db.session.query(Report).filter((Report.active == False) & (Report.url != None)).order_by(Report.id.desc()).first()

        if last_report is not None:
            df = pd.read_csv(last_report.url)

            df['air'] = df['air'] - 273.15
            df['date'] = pd.to_datetime(df.date) - datetime.timedelta(hours=5)

            last_date = df.iloc[-1].values[0]

            df_trace_1 = df.append({'date': last_date + datetime.timedelta(hours=1), 'air': None}, ignore_index=True)
            trace_1 = {'x': df_trace_1['date'], 'y': df_trace_1['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Last reports'}

            df_trace_2 = df.append({'date': last_date + datetime.timedelta(hours=1), 'air': last_report.forecast - 273.15}, ignore_index=True)
            trace_2 = {'x': df_trace_2['date'], 'y': df_trace_2['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Forecast'}

            children.append(html.P(children=f"Last updated: {last_report.created - datetime.timedelta(hours=5)}"))

            children.append(html.Div(style={'display': 'flex', 'justify-content': 'center', 'margin-top': '24px'},
                children=html.A(children=f"Download last report", href=last_report.url, download=True)))

            children.append(dcc.Graph(
                id='subplot',
                figure = {
                    'data': [trace_2, trace_1],
                    'layout': {
                        'title': 'Barranquilla, Colombia',
                        'xaxis': {'domain': [0, 1], 'title': 'Hours'},
                        'yaxis': {'domain': [0, 1], 'title': 'Celsius'}
                    }
                })
            )

        last_reports = db.session.query(Report).filter((Report.active == False) & (Report.url != None)).order_by(Report.id.desc()).all()

        data = None
        forecasts = []
        for report in last_reports:
            report_df = pd.read_csv(report.url)
            forecasts.append([report.created, report.forecast])
            if data is None:
                data = report_df
            else:
                data = data.append(report_df)

        if data is not None:
            forecast_df = pd.DataFrame(data=forecasts, columns=['date', 'air'])

            forecast_df['data'] = pd.to_datetime(forecast_df.date)
            data['date'] = pd.to_datetime(data.date)

            data = data.drop_duplicates()

            data = data.sort_values(by='date')
            forecast_df = forecast_df.sort_values(by='date')

            forecast_df['date'] = forecast_df['date'] - datetime.timedelta(hours=5)
            forecast_df['air'] = forecast_df['air'] - 273.15

            data['date'] = data['date'] - datetime.timedelta(hours=5)
            data['air'] = data['air'] - 273.15

            trace_1 = {'x': data['date'], 'y': data['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Reports saved'}
            trace_2 = {'x': forecast_df['date'], 'y': forecast_df['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Forecasts'}

            children.append(dcc.Graph(
                id='subplot',
                figure = {
                    'data': [trace_2, trace_1],
                    'layout': {
                        'title': 'Real reports vs Forecasts',
                        'xaxis': {'domain': [0, 1], 'title': 'Hours'},
                        'yaxis': {'domain': [0, 1], 'title': 'Celsius'}
                    },
                })
            )

        training_data_url = get_file('data/train_data.csv')
        
        children.append(html.Div(style={'display': 'flex', 'justify-content': 'center', 'margin-top': '24px'},
            children=html.A(children=f"Download training data", href=training_data_url, download=True)))

        training_data = pd.read_csv(training_data_url)
        training_data['air'] = training_data['air'] - 273.15

        fig = px.line(training_data, x='date', y='air', title='Training data')
        children.append(dcc.Graph(
            id='training-data',
            figure = fig,
        ))

        return children

    @dash_app.callback(dash.dependencies.Output('page-content', 'children'),
                [dash.dependencies.Input('url', 'pathname')])
    def display_page(pathname):
        if pathname == '/dashboard/' or pathname == '/dashboard' or pathname == '':
            return build_index_page()
        else:
            return html.H3('URL Error!')

    return dash_app.server
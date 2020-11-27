import os
import datetime

import dash
import plotly.express as px
import dash_core_components as dcc
import dash_html_components as html

from plotly.subplots import make_subplots

import pandas as pd

from app.database import db, Report

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

BASE_DIR = f"{os.path.abspath(os.getcwd())}/app"

def create_dashboard(server):
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/dashboard/',
        external_stylesheets=external_stylesheets
    )

    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ], id='body')

    def build_index_page():
        query = db.session.query(Report).filter((Report.active == False) & (Report.path != None)).order_by(Report.id.desc())

        children = [
            html.H1(children='Real-time temperature forecast'),
        ]

        last_report = query.first()

        if last_report is not None:
            df = pd.read_csv(last_report.path)

            df['air'] = df['air'] - 273.15
            df['date'] = pd.to_datetime(df.date) - datetime.timedelta(hours=5)

            last_date = df.iloc[-1].values[0]

            df_trace_1 = df.append({'date': last_date + datetime.timedelta(hours=1), 'air': None}, ignore_index=True)
            trace_1 = {'x': df_trace_1['date'], 'y': df_trace_1['air'], 'type':'line', 'xaxis': 'x2', 'yaxis': 'y2', 'name': 'Las data fetched'}

            df_trace_2 = df.append({'date': last_date + datetime.timedelta(hours=1), 'air': last_report.prediction - 273.15}, ignore_index=True)
            trace_2 = {'x': df_trace_2['date'], 'y': df_trace_2['air'], 'type':'line', 'xaxis': 'x2', 'yaxis': 'y2', 'name': 'Prediction'}

            children.append(html.P(children=f"Last report: {last_report.created - datetime.timedelta(hours=5)}"))
            children.append(dcc.Graph(
                id='subplot',
                figure = {
                    'data': [trace_2, trace_1],
                    'layout': {
                        'title': 'Barranquilla, Colombia',
                        'xaxis': {'domain': [0, 1]},
                        'xaxis2': {'domain': [0, 1]}
                    }
                })
            )

        last_reports = query.all()

        data = None
        for report in last_reports:
            report_df = pd.read_csv(report.path)
            if data is None:
                data = report_df
            else:
                data = data.append(report_df)

        if data is not None:
            data['air'] = data['air'] - 273.15

            fig = px.line(data, x='date', y='air', title='Last data fetched')
            children.append(dcc.Graph(
                id='last_fetched',
                figure = fig
            ))

        train_data = pd.read_csv(f"{BASE_DIR}/data/train_data.csv")
        train_data['air'] = train_data['air'] - 273.15

        fig = px.line(train_data, x='date', y='air', title='Train data')
        children.append(dcc.Graph(
            id='train_data',
            figure = fig
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
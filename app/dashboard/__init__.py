import os

import dash
import plotly.express as px
import dash_core_components as dcc
import dash_html_components as html

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

    last_report = db.session.query(Report).filter(Report.active == False).order_by(Report.id.desc()).first()
    print('last_report', last_report)

    children = [
        html.H1(children='Open weather real-time forecast'),
    ]

    if last_report is not None:
        df = pd.read_csv(last_report.path)

        fig = px.histogram(df, x="air")

        children.append(html.P(children=f"Last report: {last_report.created}"))
        children.append(dcc.Graph(
            id='example-graph',
            figure=fig
        ))

    dash_app.layout = html.Div(children=children)

    return dash_app.server
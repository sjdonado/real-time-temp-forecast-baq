import os
from datetime import timedelta
from datetime import datetime

import dash
import plotly.express as px
import dash_core_components as dcc
import dash_html_components as html
from flask_caching import Cache

from plotly.subplots import make_subplots

import pandas as pd

from app.database import db, Report
from app.services.s3 import get_file


def create_dashboard(server):
    title = 'Realtime Baq Temperature Forecast'

    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/dashboard/',
        title=title,
        assets_folder='./assets'
    )

    cache = Cache(server, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': server.config['REDIS_URI']})

    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ], id='body')

    now = datetime.now()
    timeout = (datetime(now.year, now.month, now.day, now.hour + 1, 3) - now).seconds

    # @cache.memoize(timeout=timeout)
    def build_index_page():
        children = [
            html.Div(
                [
                    html.Div(
                        [
                            html.H1(children=title),
                            html.P(children='Air temperature forecast over the first pressure level using a Long short-term memory neural network, we do not guarantee an accurate forecast.'),
                            html.A(children='Code source', href='https://github.com/sjdonado/real-time-temp-forecast-baq', target='_blank'),
                        ],
                        className="title-wrap",
                    ),
                    html.Img(
                        src=dash_app.get_asset_url('imgs/AML.png'),
                        id='aml-logo',
                    ),
                ],
                className="header",
            ),
        ]

        # last_report = db.session.query(Report).filter((Report.active == False) & (Report.url != None)).order_by(Report.id.desc()).first()
        # last_report_url = get_file(last_report.url)

        # if last_report is not None:
        #     df = pd.read_csv(last_report_url)

        #     df['air'] = df['air'] - 273.15
        #     df['date'] = pd.to_datetime(df.date) - timedelta(hours=5)

        #     last_date = df.iloc[-1].values[0]

        #     df_trace_1 = df.append({'date': last_date + timedelta(hours=1), 'air': None}, ignore_index=True)
        #     trace_1 = {'x': df_trace_1['date'], 'y': df_trace_1['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Last reports'}

        #     df_trace_2 = df.append({'date': last_date + timedelta(hours=1), 'air': last_report.forecast - 273.15}, ignore_index=True)
        #     trace_2 = {'x': df_trace_2['date'], 'y': df_trace_2['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Forecast'}

        #     children.append(html.P(children=f"Last updated: {last_report.created - timedelta(hours=5)}"))

        #     children.append(html.Div(style={'display': 'flex', 'justify-content': 'center', 'margin-top': '24px'},
        #         children=html.A(children=f"Download last report", href=last_report_url, download=True)))

        #     children.append(dcc.Graph(
        #         id='subplot',
        #         figure = {
        #             'data': [trace_2, trace_1],
        #             'layout': {
        #                 'title': 'Barranquilla, Colombia',
        #                 'xaxis': {'domain': [0, 1], 'title': 'Time'},
        #                 'yaxis': {'domain': [0, 1], 'title': 'Celsius'}
        #             }
        #         })
        #     )

        # last_reports = db.session.query(Report).filter((Report.active == False) & (Report.url != None)).order_by(Report.id.desc()).all()

        # data = None
        # forecasts = []
        # for report in last_reports:
        #     report_df = pd.read_csv(get_file(report.url))
        #     forecasts.append([report.created, report.forecast])
        #     if data is None:
        #         data = report_df
        #     else:
        #         data = data.append(report_df)

        # if data is not None:
        #     forecast_df = pd.DataFrame(data=forecasts, columns=['date', 'air'])

        #     forecast_df['data'] = pd.to_datetime(forecast_df.date)
        #     data['date'] = pd.to_datetime(data.date)

        #     data = data.drop_duplicates()

        #     data = data.sort_values(by='date')
        #     forecast_df = forecast_df.sort_values(by='date')

        #     forecast_df['date'] = forecast_df['date'] - timedelta(hours=6)
        #     forecast_df['air'] = forecast_df['air'] - 273.15

        #     data['date'] = data['date'] - timedelta(hours=5)
        #     data['air'] = data['air'] - 273.15

        #     trace_1 = {'x': data['date'], 'y': data['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Real reports'}
        #     trace_2 = {'x': forecast_df['date'], 'y': forecast_df['air'], 'type':'line', 'xaxis': 'x1', 'yaxis': 'y1', 'name': 'Forecasts'}

        #     children.append(dcc.Graph(
        #         id='subplot',
        #         figure = {
        #             'data': [trace_2, trace_1],
        #             'layout': {
        #                 'title': 'Real reports vs Forecasts',
        #                 'xaxis': {'domain': [0, 1], 'title': 'Time'},
        #                 'yaxis': {'domain': [0, 1], 'title': 'Celsius'}
        #             },
        #         })
        #     )

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
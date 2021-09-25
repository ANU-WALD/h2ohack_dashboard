import math
import os
import urllib.request
import json
import numpy as np
import pandas as pd
import geopandas as gpd

import dash
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc
import dash_auth
from dash_extensions.javascript import arrow_function
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

import plotly.express as px

geojson_url = 'https://gist.githubusercontent.com/prl900/fd34fe289916851a80daa4b19f5a4c11/raw/c84503815aa5fd72caa9ed877bb0b42434049272/boundary.geojson'

with urllib.request.urlopen(geojson_url) as url:
    data = json.loads(url.read().decode())

geojson = dl.GeoJSON(id="geojson",
                     data=data,
                     zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. cluster) on click
                     hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')))


def get_info(feature=None):
    header = [html.H4("Catchment areas")]
    if not feature:
        return header + ["Hover over a region"]
    return header + [html.B(feature["properties"]["AlbersArea"])]

info = html.Div(children=get_info(), id="info", className="info",
                style={"position": "absolute", "top": "10px", "right": "10px", "z-index": "1000"})

app = dash.Dash(external_stylesheets=[dbc.themes.YETI])


dem = dl.WMSTileLayer(id= 'dem-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="ELVIS_UTM", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z"), transparent=True)
flood = dl.WMSTileLayer(id= 'flood-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="Flood", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z", threshold=100), transparent=True)


app.layout = dbc.Container([
    dbc.Row([
            dbc.Col(html.H1('WALD H2OHack - Interactive Dashboard', style={'marginTop': 35}), width=10),
            dbc.Col(html.Div(html.Img(src=app.get_asset_url('floodplain.png'), style={'height':'100%','width':'100%', 'marginTop': 10})), width=2)
        ]),
    dbc.Row([
            dbc.Col(dl.Map(children=[dl.TileLayer(), dem, flood, geojson, info], center=[-30.0,146], zoom=10), width=8, className='mt-1', style={'width': '100%', 'height': '60vh', 'margin': "auto", "display": "block", "position": "relative"}),
            dbc.Col([
                html.Div([
                    dbc.Label("Inundation Level"),
                    dcc.Slider(id="sld_height", min=100, max=120, value=100, marks={
                            100: {'label': '100'},
                            100: {'label': '105'},
                            110: {'label': '110'},
                            110: {'label': '115'},
                            120: {'label': '120'}
                        },
                        included=False
                    ),
                ]), 
                html.Div([
                    dbc.Label("Temporal evolution"),
                    dcc.Graph(id="graph"),
                ])
            ], width=4, className='mt-1', style={'width': '100%', 'height': '50vh', 'margin': "auto", "display": "block", "position": "relative"})
        ]),
    ], fluid=True)

@app.callback(
        Output("info", "children"), 
        [Input("geojson", "hover_feature")])
def info_hover(feature):
    return get_info(feature)

@app.callback(
    Output("flood-wms", "extraProps"),
    Input("sld_height", "value"))
def info_click(height):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    return dict(threshold=height)

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True, use_reloader=False)

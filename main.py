import math
import os
from urllib import request
import json
import pandas as pd

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
import plotly.graph_objects as go

# Sat baselayer
hires_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

# Subcatchment polygons disabled
"""
geojson_url = 'https://gist.githubusercontent.com/prl900/d385b83aac5421f05edc88b14a5b7e80/raw/28ec913833827a9f58e9251717b7eac43aeb7e29/catchments.geojson'

with urllib.request.urlopen(geojson_url) as url:
    data = json.loads(url.read().decode())

geojson = dl.GeoJSON(id="geojson",
                     data=data,
                     zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. cluster) on click
                     hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')))
"""


def get_info(feature=None):
    header = [html.H4("Catchment areas")]
    if not feature:
        return header + ["Hover over a region"]
    return header + [html.B(feature["properties"]["AlbersArea"])]

info = html.Div(children=get_info(), id="info", className="info",
                style={"position": "absolute", "top": "10px", "right": "10px", "z-index": "1000"})

app = dash.Dash(external_stylesheets=[dbc.themes.YETI])


# Terrain layer disabled (using satellite baselayer instead)
#dem = dl.WMSTileLayer(id= 'dem-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="ELVIS_UTM", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z"), transparent=True)
flood = dl.WMSTileLayer(id= 'flood-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="Flood", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z", threshold=100), transparent=True)


### Sample figure for the hypsometric
z_data = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/api_docs/mt_bruno_elevation.csv')
fig = go.Figure(data=[go.Surface(z=z_data.values)])
fig.update_layout(title='Mt Bruno Elevation', autosize=False,
                  width=500, height=500,
                  margin=dict(l=65, r=50, b=65, t=90))


app.layout = dbc.Container([
    dbc.Row([
            dbc.Col(html.H1('WALD H2OHack - Interactive Dashboard 2', style={'marginTop': 35}), width=10),
            dbc.Col(html.Div(html.Img(src=app.get_asset_url('floodplain.png'), style={'height':'100%','width':'100%', 'marginTop': 10})), width=2)
        ]),
    dbc.Row([
            dbc.Col(dl.Map(children=[
                dl.TileLayer(url=hires_url), 
                dl.FeatureGroup([
                    dl.EditControl(id="edit_control", draw=dict(circle=False, circlemarker=False))
                ]), 
                flood, 
                info
            ], center=[-30.0,146.3], zoom=10), width=8, className='mt-1', style={'width': '100%', 'height': '60vh', 'margin': "auto", "display": "block", "position": "relative"}),
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
                    dcc.Graph(id="graph", figure=fig),
                ])
            ], width=4, className='mt-1', style={'width': '100%', 'height': '50vh', 'margin': "auto", "display": "block", "position": "relative"})
        ]),
    ], fluid=True)

# Geojson polygon clicking callback disabled
"""
@app.callback(
        Output("info", "children"), 
        [Input("geojson", "hover_feature")])
def info_hover(feature):
    return get_info(feature)
"""

# This updated the WMS flooding layer with the new threshold
@app.callback(
    Output("flood-wms", "extraProps"),
    Input("sld_height", "value"))
def info_click(height):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    return dict(threshold=height)

# This displays flooded area and volume in the map's info panel
@app.callback(Output("info", "children"), Input("edit_control", "geojson"), Input("sld_height", "value"))
def water_request(geojson, threshold):

    if geojson and len(geojson['features']) > 0:
        data = json.dumps({"product": "ELVIS_UTM", "threshold": threshold, "feature": geojson['features'][-1]})
        req =  request.Request("https://h2ohack-mtmenipwta-ts.a.run.app/wps", data=data.encode())
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        resp = request.urlopen(req)

        df = pd.read_csv(resp, parse_dates=[0], index_col=0, header=0)

        return f"Area: {df.iloc[0,1]/10000:.2f} ha | Volume: {df.iloc[0,0]/1000:.2f} ML"

    return ""


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True, use_reloader=False)

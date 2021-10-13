import math
import os
from urllib import request
import json
import pandas as pd
import numpy as np
from io import BytesIO

import dash
import dash_leaflet as dl
import dash_table
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

grace_drought_data = "https://gist.githubusercontent.com/prl900/32055725184581317308cd5e1af8e8eb/raw/88381eb60fb06ee5d5beb5620e0f4c930302eee6/GRACE_drought_index.csv"

df = pd.read_csv(grace_drought_data, index_col=1, parse_dates=True)
drought_fig = px.line(df, y="Drought_Index_Value")
drought_fig.update_layout(margin=dict(t=5,r=5,l=5,b=5))
drought_fig.add_hrect(y0=-2.6, y1=-1.5, line_width=0, fillcolor="red", opacity=0.3)
drought_fig.add_hrect(y0=-1.5, y1=0, line_width=0, fillcolor="orange", opacity=0.3)
drought_fig.add_hrect(y0=0, y1=1.5, line_width=0, fillcolor="lightgreen", opacity=0.3)
drought_fig.add_hrect(y0=1.5, y1=3.2, line_width=0, fillcolor="green", opacity=0.3)

cross_fig = go.Figure(data=[go.Surface(z=np.ones((400,400)), colorscale='Viridis')])
cross_fig.update_layout(autosize=False, width=300, height=300, margin=dict(l=5, r=5, b=5, t=5))
cross_fig.update_traces(showscale=False)

terrain_fig = go.Figure(data=[go.Surface(z=np.ones((400,400)))])
terrain_fig.update_layout(autosize=False, width=300, height=300, margin=dict(l=5, r=5, b=5, t=5))
terrain_fig.update_traces(showscale=False)

table = dash_table.DataTable(
    id='table',
    columns=[{"name": i, "id": i} for i in df.columns],
    data=df.to_dict('records'),
    page_action="native",
    page_current= 0,
    page_size= 10,
)

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

app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY])


# Terrain layer disabled (using satellite baselayer instead)
#dem = dl.WMSTileLayer(id= 'dem-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="ELVIS_UTM", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z"), transparent=True)
#flood = dl.WMSTileLayer(id= 'flood-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="Flood", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z", threshold=100), transparent=True)
flood = dl.WMSTileLayer(id= 'flood-wms', url="https://h2ohack-mtmenipwta-ts.a.run.app/wms", layers="FloodViridis", format="image/png", extraProps=dict(time="2021-01-01T00:00:00.000Z", threshold=100), transparent=True)


app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1('OzRiver H2OHack - Interactive Water Trading Dashboard', style={'marginTop': 35}), width=11),
        dbc.Col(html.Div(html.Img(src=app.get_asset_url('floodplain.png'), style={'height':'100%','width':'100%', 'marginTop': 10})), width=1)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Label("Drought Period"),
            dcc.Slider(id="sld_drought", min=1960, max=2021, value=2020, marks={
                    1960: {'label': '1960'},
                    1970: {'label': '1970'},
                    1980: {'label': '1980'},
                    1990: {'label': '1990'},
                    2000: {'label': '2000'},
                    2010: {'label': '2010'},
                    2020: {'label': '2020'},
                },
                included=False
            ),
            dbc.Label("Historical Drought"),
            dcc.Graph(id="drought-fig", figure=drought_fig, style={'height': '35vh'}, config={'displayModeBar': False}),
            dbc.Label("Inundation Level"),
            dcc.Slider(id="sld_height", min=100, max=120, value=100, marks={
                                100: {'label': '100'},
                                100: {'label': '105'},
                                110: {'label': '110'},
                                110: {'label': '115'},
                                120: {'label': '120'}}, included=False),
        ], width=4),
        dbc.Col([
            dl.Map(children=[
                    dl.TileLayer(url=hires_url), 
                    dl.FeatureGroup([
                        dl.EditControl(id="edit_control", draw=dict(circle=False, circlemarker=False))
                    ]), 
                    flood, 
                    info
            ], center=[-30.0,146.4], zoom=10),
        ], width=8, className='mt-1', style={'width': '100%', 'height': '60vh', 'margin': "auto", "display": "block", "position": "relative"}),
    ]),
    dbc.Row([
        dbc.Col([
            #html.Div([
                dbc.Label("Cross Section"),
                dcc.Graph(id="time-graph", figure=cross_fig),
            #]),
        ], width=2),
        dbc.Col([
            #html.Div([
                dbc.Label("Terrain Model"),
                dcc.Graph(id="3d-graph", figure=terrain_fig),
            #]),
        ], width=2),
        dbc.Col([
            dbc.Label("Table data (placeholder)"),
            table
        ], width=8),
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


# This displays flooded area and volume in the map's info panel
@app.callback(Output("3d-graph", "figure"), Input("edit_control", "geojson"), Input("sld_height", "value"))
def terrain_3d(geojson, threshold):
    
    if geojson is None:
        raise PreventUpdate

    if len(geojson['features']) == 0:
        raise PreventUpdate
   
    if geojson['features'][0]['geometry']['type'] != 'Polygon':
        raise PreventUpdate
    
    data = json.dumps({"product": "ELVIS_UTM", "feature": geojson['features'][0]})
    req =  request.Request("https://h2ohack-mtmenipwta-ts.a.run.app/wcs", data=data.encode())
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    resp = request.urlopen(req)

    terrain = np.load(BytesIO(resp.read()))
    terrain[terrain==-9999] = np.nan
    water_level = np.ones(terrain.shape)*threshold

    fig = go.Figure(data=[go.Surface(z=terrain), go.Surface(z=water_level, colorscale="ice")])
    fig.update_layout(title='3D Model', autosize=False,
                  width=300, height=300,
                  margin=dict(l=5, r=5, b=5, t=5))
    fig.update_traces(showscale=False)
    
    return fig


# This displays flooded area and volume in the map's info panel
@app.callback(Output("time-graph", "figure"), Input("edit_control", "geojson"), Input("sld_height", "value"))
def water_request(geojson, threshold):
    
    if geojson is None:
        raise PreventUpdate

    if len(geojson['features']) == 0:
        raise PreventUpdate
   
    if geojson['features'][-1]['geometry']['type'] != 'LineString':
        raise PreventUpdate
    
    data = json.dumps({"product": "ELVIS_UTM", "feature": geojson['features'][-1]})
    req =  request.Request("https://h2ohack-mtmenipwta-ts.a.run.app/wcs", data=data.encode())
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    resp = request.urlopen(req)

    terrain = np.fromstring(resp.read().decode().rstrip().strip('[]'), sep=',')
    terrain = np.tile(terrain, (terrain.shape[0], 1))

    water_level = np.ones(terrain.shape)*threshold

    fig = go.Figure(data=[go.Surface(z=terrain), go.Surface(z=water_level, colorscale="ice")])
    fig.update_layout(title='Cross-section', autosize=False,
                  width=300, height=300,
                  margin=dict(l=5, r=5, b=5, t=5))
    fig.update_traces(showscale=False)
    
    return fig


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True, use_reloader=False)

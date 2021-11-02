import math
import os
from urllib import request
import json
import pandas as pd
import geopandas as gpd
import numpy as np
from io import BytesIO

import dash
from dash import html
from dash import dcc
from dash import dash_table
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash_extensions.javascript import arrow_function
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go

# Sat baselayer
hires_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

# polygons
geojson_url = 'https://gist.githubusercontent.com/prl900/d590466b9cc6d8f4400446b0533a1900/raw/3c4053be5c04607d865be865fc14e659d62937c4/Act_HIR_NFMR_Projects.geojson'

data = None
with request.urlopen(geojson_url) as url:
    data = json.loads(url.read().decode())

geojson = dl.GeoJSON(id="geojson",
                     data=data,
                     zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. cluster) on click
                     hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')))

gdf = gpd.read_file(geojson_url)
gdfc = gdf.to_crs('epsg:3577')
gdf["area"] = gdfc['geometry'].area/1e4

projects = gdf["proj_id"].values

geojson_dyn = dl.GeoJSON(id="geojson_dyn",
                     data=data,
                     options=dict(style=dict(opacity=0, fillOpacity=0)),
                     zoomToBounds=True)


def drill_natforest(feat):
    pyld = json.dumps({"product": "nfswv", "feature": feat})
    req =  request.Request("https://nfswv-mtmenipwta-ts.a.run.app/wps", data=pyld.encode())
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    resp = request.urlopen(req)

    df = pd.read_csv(resp, parse_dates=[0], index_col=0, header=0)
    df.replace(0, np.nan, inplace=True)

    return df

def drill_anuforest(feat):
    pyld = json.dumps({"layer_name": "wcf", "vector": feat})
    req =  request.Request("https://australia-southeast1-wald-1526877012527.cloudfunctions.net/tree-change-drill", data=pyld.encode())
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    resp = request.urlopen(req)

    df = pd.read_csv(resp, parse_dates=[0], index_col=0, header=None)
    df.columns = ["ANU Woody Cover Fraction"]

    return df

def drill_prec(feat):
    var_name = "MSWX_precipitation"
    pyld = json.dumps({"product": var_name, "feature": feat})
    req =  request.Request("https://australia-southeast1-wald-1526877012527.cloudfunctions.net/mswx-tx", data=pyld.encode())
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    resp = request.urlopen(req)

    df = pd.read_csv(resp, parse_dates=[0], names=[f'{var_name} mean', f'{var_name} pixels'], index_col=0, header=0)
    df.drop(columns=[f'{var_name} pixels'], inplace=True)
    df.sort_index(inplace=True)
    df[f'{var_name} mean'] = pd.to_numeric(df[f'{var_name} mean'], downcast="float")
    df = df.loc['1989-01-01':'2020-12-31']
    df = df.resample('1Y').sum()

    return df

def get_info(feature=None):
    header = [html.H4("Reforestation Projects")]
    if not feature:
        return header + ["Hover over a region"]
    area = gdf[gdf["proj_id"]==feature["properties"]["proj_id"]].iloc[0]['area']
    return header + [html.B(f"{feature['properties']['proj_id']} -- {area:.2f} ha")]


info = html.Div(children=get_info(), id="info", className="info",
                style={"position": "absolute", "top": "10px", "right": "10px", "z-index": "1000"})

app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    dcc.Store(id='memory-output'),
    dbc.Row([
        dbc.Col(html.H1('National Forest Assesment Dashboard', style={'marginTop': 35}), width=10),
        #dbc.Col(html.Div(html.Img(src=app.get_asset_url('floodplain.png'), style={'height':'100%','width':'100%', 'marginTop': 20})), width=2)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Label("Project ID", size='lg'), 
            dcc.Dropdown(id='sel_project', value=None, options=[{'label': str(i), 'value': i} for i in projects])
        ], width=2),
        dbc.Col([
            dbc.Label("Dataset", size='lg'), 
            dcc.Dropdown(id='dataset', value=None, options=[{'label': "National Forest", 'value': 'nfswv'}])
        ], width=2),
        dbc.Col([
            dbc.Label("Year Selection", size='lg'),
            dcc.Slider(id="sld_year", min=1988, max=2020, value=2020, marks={y:{'label':str(y)} for y in range(1988,2021,2)}, included=False),
        ], width=8),
    ]),
    dbc.Row([
        dbc.Col([
            dl.Map(children=[
                    dl.LayersControl([
                        dl.BaseLayer(dl.TileLayer(), name="map", checked=False),
                        dl.BaseLayer(dl.TileLayer(url=hires_url), name="satellite", checked=True),
                        dl.Overlay(dl.WMSTileLayer(id='natfor-wms', url="https://nfswv-mtmenipwta-ts.a.run.app/wms", layers="nfswv", format="image/png", opacity=0.8, extraProps=dict(time="2020-01-01T00:00:00.000Z")), name='National Forest', checked=True),
                    ], position='bottomleft'),
                    info,
                    geojson_dyn,
                    geojson,
            ], center=[-30.0,146.4], zoom=6, style={'height': '80vh'}),
        ], width=8),
        dbc.Col([
            dbc.Label("National Forest Data", size='lg'), 
            dcc.Loading(dcc.Graph(id='nf-chart', figure=px.scatter(), style={'height': '25vh'})),
            dbc.Label("ANU WCF", size='lg'), 
            dcc.Loading(dcc.Graph(id='anu-chart', figure=px.scatter(), style={'height': '25vh'})),
            dbc.Label("Precipitation", size='lg'), 
            dcc.Loading(dcc.Graph(id='prec-chart', figure=px.scatter(), style={'height': '25vh'})),
        ], width=4),
    ]),
], fluid=True)

# Geojson polygon clicking callback disabled
@app.callback(
        Output("info", "children"), 
        [Input("geojson", "hover_feature")])
def info_hover(feature):
    return get_info(feature)

# This displays flooded area and volume in the map's info panel
@app.callback(Output("natfor-wms", 'extraProps'), Input("sld_year", "value"))
def aet_wms(year):

    return dict(time=f"{year}-01-01T00:00:00.000Z")


# This displays flooded area and volume in the map's info panel
@app.callback(Output("sel_project", "value"), Input("geojson", "click_feature"))
def update_proj_selector(geojson):
    if not geojson:
        raise PreventUpdate
    
    return geojson['properties']['proj_id']


# This displays flooded area and volume in the map's info panel
@app.callback(Output("geojson_dyn", "data"), Input("sel_project", "value"))
def zoom_in_selection(project_id):
    fdata = data.copy()

    for feat in fdata["features"]:
        if feat["properties"]["proj_id"] == project_id:
            fdata["features"] = [feat]
            return fdata

    return dash.no_update


@app.callback(Output("nf-chart", "figure"), Input("sel_project", "value"))
def update_nf_figure(project_id):

    for feat in data["features"]:
        if feat["properties"]["proj_id"] == project_id:
            df = drill_natforest(feat)
            fig = px.line(df, markers=True)
            fig.update_layout(margin=dict(t=5,r=5,l=5,b=5))
            fig.update_layout(legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1,
                xanchor="right",
                x=1
            ))

            return fig

    return dash.no_update


@app.callback(Output("anu-chart", "figure"), Input("sel_project", "value"))
def update_anu_figure(project_id):

    for feat in data["features"]:
        if feat["properties"]["proj_id"] == project_id:
            df = drill_anuforest(feat)
            fig = px.line(df, markers=True)
            fig.update_layout(margin=dict(t=5,r=5,l=5,b=5))
            fig.update_layout(legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1,
                xanchor="right",
                x=1
            ))

            return fig

    return dash.no_update

@app.callback(Output("prec-chart", "figure"), Input("sel_project", "value"))
def update_prec_figure(project_id):

    for feat in data["features"]:
        if feat["properties"]["proj_id"] == project_id:
            df = drill_prec(feat)
            fig = px.bar(df)
            fig.update_layout(margin=dict(t=5,r=5,l=5,b=5))
            fig.update_layout(legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1,
                xanchor="right",
                x=1
            ))

            return fig

    return dash.no_update


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True, use_reloader=False)

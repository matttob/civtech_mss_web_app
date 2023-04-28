#Import PLotly Dash , Dash Leaflet (for mapping), Jupyter Dash (for using dash/dash leaflet in notebook),
# Import  Json & httpx for getting data from TiTiler 
from dash import Dash, html,dcc,Input, Output, callback_context
import dash_leaflet as dl
import dash_leaflet.express as dlx  
import json
import httpx
import numpy as np
import random
from dash_extensions.javascript import assign, Namespace
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import rasterio
import rasterio.mask
from PIL import Image
import time
from osgeo import ogr
import copy
from osgeo import osr
import base64
ns = Namespace('dashExtensions','dashExtensionssub')


# Enter tiler details
titiler_endpoint= "https://os8ci3nx02.execute-api.eu-west-2.amazonaws.com"  # titiler running on AWS Lamda
# titiler_endpoint = "http://localhost:8080" 

# survey json file list
survey_json_paths = [
                    '/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/meta_data/ard_bay_2023.json',
                    '/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/meta_data/creran_2023.json'
]

# load all jsons could maybe load on demand in future
survey_json_list = []
for  survey in survey_json_paths:
    with open(survey, 'r') as openfile:
        survey_json = json.load(openfile)
    survey_json_list.append(survey_json)




# Style and Images
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
logo_image_path = 'assets/Logo2.png'


def create_tile_request(url):
    tile_request = httpx.get(
        f"{titiler_endpoint}/cog/tilejson.json",
        params = {
            "url": url,
            "rescale": f"{0},{255}",
        }
    ).json()
    return tile_request


def update_species_df(survey_json_list_ind):
    species_df = pd.DataFrame([survey_json_list[survey_json_list_ind]['species_name']],columns=['Species'])
    species_df['coverage_sqm']= [survey_json_list[survey_json_list_ind]['species_m2']]
    return species_df
    
def update_species_plots(species_df):    

    species_bar = px.bar(species_df,x='Species',y='coverage_sqm',
                            labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (Testing)'},
                            range_y=[0, 20])
    species_bar.update_layout(
    showlegend=False,
    xaxis = dict(
        showgrid=False),
    yaxis=dict(showgrid=False),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")
    return species_bar



def set_map_view(map_view,survey_json_list_ind):
    map_view['center'] =  [survey_json_list[survey_json_list_ind]['centre_coords'][1], survey_json_list[survey_json_list_ind]['centre_coords'][0]]
    map_view['zoom'] = 20
    return map_view



# Initialise species ID data frames
species_df_initial = pd.DataFrame([''],columns=['Species'])
species_df_initial['coverage_sqm']= 0

species_time_series_df_initial_counts = [0]
species_time_series_df_initial_years = [2022,2023]
species_time_series_df_initial = pd.DataFrame(list(zip(species_time_series_df_initial_years, species_time_series_df_initial_counts)),
               columns =['year', 'pixel_area_count'])


# Initialise species ID plots
species_bar = px.bar(species_df_initial,x='Species',y='coverage_sqm', color='Species',
                     color_discrete_map={'pink':'DeepPink'},
                     labels={'Species': '','coverage_sqm': 'Area Covered  (Testing) '},
                     range_y=[0, 8])
species_bar.update_layout(
     showlegend=False,
    xaxis = dict(
        showgrid=False),
         yaxis=dict(showgrid=False),
         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")



# marker testing

marker= [dict(name=survey_json_list[0]['species_name'], iso2='alcyonium_digitatum_icon_red',lat=survey_json_list[0]['centre_coords'][1], lon=survey_json_list[0]['centre_coords'][0]),
            dict(name=survey_json_list[1]['species_name'], iso2='serp_icon_red', lat=survey_json_list[1]['centre_coords'][1], lon=survey_json_list[1]['centre_coords'][0])]

geojson = dlx.dicts_to_geojson([{**c, **dict(tooltip=c['name'])} for c in marker])











# create dash app
app = Dash(__name__)

#create the info panel where text can be displayed
info = html.Div( id="info", className="info",
                style={"position": "absolute", "bottom": "10px", "left": "10px", "z-index": "1000"})

plots = html.Div(id="plots", className="plots",style={"position": "absolute", "bottom": "10px", "right": "10px", "z-index": "1000"},children = [
dcc.Graph(id='species_bar',
            figure=species_bar,style={'width': '300px', 'height': '300px','float': 'left','margin': '1px'})])

trito_logo = html.Div(id="trito_logo", className="trito_logo",
                      style={"position": "absolute", "bottom": "50px", "left": "10px", "z-index": "1000"},
                      children = [html.Img(src=logo_image_path,style={'height':'10%', 'width':'10%'})])

# Set map default view
start_zoom = 8
map_centre_coords = [56.5314423498172, -5.619001454153479]
initial_map_children=[ 
                dl.LayersControl([
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_tile_request(survey_json_list[0]["COG_ARN"])["tiles"][0],
                                                      id=survey_json_list[0]['survey_dash_id'])),name=survey_json_list[0]['survey_long_name'],checked=True),
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_tile_request(survey_json_list[0]["COG_ARN_species"])["tiles"][0],
                                                      id=survey_json_list[0]['survey_dash_id']+'species')),name=survey_json_list[0]['survey_long_name']+'species',checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_tile_request(survey_json_list[1]["COG_ARN"])["tiles"][0],
                                                      id=survey_json_list[1]['survey_dash_id'])),name=survey_json_list[1]['survey_long_name'],checked=True),
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_tile_request(survey_json_list[1]["COG_ARN_species"])["tiles"][0],
                                                      id=survey_json_list[1]['survey_dash_id']+'species')),name=survey_json_list[1]['survey_long_name']+'species',checked=True),
                dl.LayerGroup(id="layer"),
                
                dl.GeoJSON(data=geojson, options=dict(pointToLayer=ns('draw_icon')),id='geojson'),
                plots,
                info,
                trito_logo]),

                ]



#Create app layout 

survey_drop_down_list_items =[survey_long_name['survey_long_name'] for survey_long_name in survey_json_list]
survey_drop_down_list_items.append('none')
app.layout = html.Div([
dl.Map(style={'width': '1600px', 'height': '800px','margin': '30px'},
            center=map_centre_coords,
            zoom=start_zoom,
            maxZoom=1000,
            id = "map",
            children=initial_map_children),
html.Div(children=[
            html.Label(['Select Survey:'], style={'font-weight': 'bold', "text-align": "center"}),
            dcc.Dropdown(id = 'survery_select',
                        options=survey_drop_down_list_items,
                        value='none',  # initial value displayed when page first loads
                        clearable=False)],
                        style=dict(width='25%')),
dcc.Store(id = 'intermediate_mapview'),
dcc.Store(id = survey_json_list[0]['survey_dash_id']+'_click_intermediate'),
dcc.Store(id = 'intermediate_marker_hover'),
])



@app.callback(Output("species_bar",component_property='figure'),
              Output('intermediate_mapview','data'),
              Output("survery_select", component_property='value'),
              Output("map", "viewport"),
              Output("info",component_property='children'),
              Output(survey_json_list[0]['survey_dash_id']+'_click_intermediate','data'),
              Output('intermediate_marker_hover','data'),
              Input("map", "viewport"),
              Input("survery_select", component_property='value'),
              Input('intermediate_mapview','data'),
              Input('geojson', 'n_clicks'),
              Input(survey_json_list[0]['survey_dash_id']+'_click_intermediate','data'),
              Input('geojson', 'hover_feature'),
              Input('intermediate_marker_hover','data')
              )

def update_map_and_graphics(map_view,survey_name,intermediate_mapview,marker_clicks_0,
                                   intermediate_clicks_0,marker_hover,intermediate_marker_hover):
    ctx = callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print(input_id)

    # crude way to stop control of map view if user moves map
    if map_view != intermediate_mapview:
        survey_name_out = 'none'
    else:
        survey_name_out=survey_name

 
    # if not marker_hover:
    #     marker_hover = 'no_hover'



    # for some reason 1st time page loads there is no input from app from map:viewport
    if map_view is None:
          map_view = {'center': [56.58215811323581, -5.701866236751068], 'zoom': 9}
          map_children=initial_map_children
    
    # If statements for each case of the dropdown menu - 
    # this must be improved also at present the entire child of the map is being changed even 
    # though in most cases there are some layers that are not being updated
    if not marker_hover:
        marker_hover =  {'properties': {'name': '123'}}

    


    
    if   (marker_hover['properties']['name'] == survey_json_list[0]['species_name'] or marker_hover['properties']['name'] == '123') and  marker_clicks_0 !=  intermediate_clicks_0  :
        set_map_view(map_view,0)
        species_df = update_species_df(0)
        species_bar = update_species_plots(species_df)
        survey_name = survey_json_list[0]['survey_long_name'] 
    
    elif   (marker_hover['properties']['name'] == survey_json_list[0]['species_name']) and input_id == 'geojson':
            species_df = update_species_df(0)
            species_bar = update_species_plots(species_df)
            survey_name = survey_json_list[0]['survey_long_name'] 

    elif(marker_hover['properties']['name'] == survey_json_list[1]['species_name'] or marker_hover['properties']['name'] == '123') and marker_clicks_0 !=  intermediate_clicks_0 and input_id != geojson :
        set_map_view(map_view,1)
        species_df = update_species_df(1)
        species_bar = update_species_plots(species_df)
        survey_name = survey_json_list[1]['survey_long_name'] 
    
    elif   (marker_hover['properties']['name'] == survey_json_list[1]['species_name']) and input_id == 'geojson':
        species_df = update_species_df(1)
        species_bar = update_species_plots(species_df)
        survey_name = survey_json_list[1]['survey_long_name'] 


    elif survey_name == survey_json_list[0]['survey_long_name'] :
        set_map_view(map_view,0)
        species_df = update_species_df(0)
        species_bar = update_species_plots(species_df)
    

    elif survey_name == survey_json_list[1]['survey_long_name']:
        set_map_view(map_view,1)
        species_df = update_species_df(1)
        species_bar = update_species_plots(species_df)

    else:

        species_df = species_df_initial
        species_bar = update_species_plots(species_df)




    
    
    
    if marker_clicks_0:
        intermediate_clicks_0 =  marker_clicks_0


    # first time call backs fire no intermediate value
    if not intermediate_mapview:
        intermediate_mapview = map_view


    # update info box with file name used for metrics
    info_out = str(survey_name)
    
    return  species_bar,  intermediate_mapview, survey_name_out, map_view, info_out,  intermediate_clicks_0, intermediate_marker_hover





if __name__ == '__main__':
    app.run_server(debug=True,port=8053)
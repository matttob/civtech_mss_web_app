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
import geopandas as gpd 
import numpy as np
import pandas as pd     
import fiona
ns = Namespace('dashExtensions','dashExtensionssub')

# survey json file list
survey_json_paths = ['/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/meta_data/ard_bay_2022.json', 
                     '/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/meta_data/creran_2023.json']

# load all jsons could maybe load on demand in future
survey_json_list = []
for  survey in survey_json_paths:
    with open(survey, 'r') as openfile:
        survey_json = json.load(openfile)
    survey_json_list.append(survey_json)
survey_df = pd.DataFrame.from_dict(survey_json_list)

# Style and Images
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
logo_image_path = 'assets/Logo2.png'

def create_marble_cutter_tile(url):
    marble_tile_request = httpx.get(f"http://tiles.rdnt.io/tiles?url={url}",
        params = {
  "maxzoom": 100,
  "minzoom": 1,
  "name": "Untitled",
  "tilejson": "2.1.0",
  "tiles": [
    f"//tiles.rdnt.io/tiles/{{z}}/{{x}}/{{y}}?url={url}"
  ]
}).json()
    return marble_tile_request                               

def set_map_view(map_view,survey_dash_id,survey_df):
    coords = list((survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['centre_coords'].values[0]))
    map_view['center'] =  coords
    map_view['zoom'] = 20
    return map_view

def write_info_out(survey_dash_id,survey_df):
    if  len(survey_dash_id) > 0:
        info_out = ("** Survey Name** : " +  str(survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['survey_long_name'].values[0]) + " \n" + " \n" + 
                    "**Species Present** : " + str(survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['species_name'].values[0]) + " \n" + " \n" + 
                    "**Total Area of Species : **" + str(survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['species_m2'].values[0]) + " \n" + " \n" + 
                    "**Number of Individuals : **" + str(survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['number_of_individuals'].values[0]) + " \n" + " \n" + 
                    "**Natural Capital Potential : **" + str(survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['nat_cap_potential_description'].values[0]) + " \n" + " \n" + 
                    "**Natural Capital Value : **" + str(survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]['nat_cap_value'].values[0]))
    else:
        info_out = ("** Survey Name** : " + " \n" + " \n" + 
                    "**Species Present** : "  + " \n" + " \n" + 
                    "**Total Area of Species : **"  + " \n" + " \n" + 
                    "**Number of Individuals : **"  + " \n" + " \n" + 
                    "**Natural Capital Potential : **"  + " \n" + " \n" + 
                    "**Natural Capital Value : **" ) 
    return info_out

# Survey position markers
marker= [dict(name=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['species_name'].values[0], 
            iso2='alcyonium_digitatum_icon_red',
            lat=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['centre_coords'].values[0][0], 
            lon=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['centre_coords'].values[0][1]),
        dict(name=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['species_name'].values[0], 
            iso2='serp_icon_red',
            lat=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['centre_coords'].values[0][0], 
            lon=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['centre_coords'].values[0][1])]
geojson = dlx.dicts_to_geojson([{**c, **dict(tooltip=c['name'])} for c in marker])

# serpulid species marker testing
fiona.drvsupport.supported_drivers['KML'] = 'rw'
df = gpd.read_file('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/species_locations/Serpulids.kml',driver='KML')
df['lat'] = df.geometry.apply(lambda p: p.y)
df['lon'] = df.geometry.apply(lambda p: p.x)
df = df[['lat', 'lon']]
df['name'] = survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['species_name'].values[0]
df['iso2'] = ['serp_individual'] * len(df['lat'])
serp_markers = df.to_dict('rows')
geojson_serp = dlx.dicts_to_geojson([{**c, **dict(tooltip=c['name'])} for c in serp_markers])



# create dash app
app = Dash(__name__)

#create the info panel where text can be displayed
info = html.Div(dcc.Markdown(id="info", className="info",
                style={"position": "absolute", "bottom": "50px", "left": "1100px", "z-index": "1000", 'width':'270px'}))

trito_logo = html.Div(id="trito_logo", className="trito_logo",
                      style={"position": "absolute", "bottom": "10px", "left": "10px", "z-index": "1000"},
                      children = [html.Img(src=logo_image_path,style={'height':'10%', 'width':'10%'})])

# Set map default view

start_zoom = 10
map_centre_coords = [56.5314423498172, -5.619001454153479]
initial_map_children=[ 
                dl.LayersControl([
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_marble_cutter_tile(survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['COG_ARN'].values[0])['tiles'][0],
                                                      id= survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['survey_dash_id'].values[0])),
                                                      name=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['survey_long_name'].values[0],checked=True),

                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_marble_cutter_tile(survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['COG_ARN_species'].values[0])['tiles'][0],opacity=0.4,
                                                      id= survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['survey_dash_id'].values[0] + '_species')),
                                                      name=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['survey_long_name'].values[0],checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_marble_cutter_tile(survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['COG_ARN'].values[0])['tiles'][0],
                                                      id= survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['survey_dash_id'].values[0])),
                                                      name=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['survey_long_name'].values[0],checked=True),

                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_marble_cutter_tile(survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['COG_ARN_species'].values[0])['tiles'][0],opacity=0.4,
                                                      id= survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['survey_dash_id'].values[0] + '_species' )) ,
                                                      name=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['survey_long_name'].values[0],checked=True),            


                dl.LayerGroup(id="layer"),
                dl.GeoJSON(data=geojson_serp, options=dict(pointToLayer=ns('draw_icon')),id='geojson_serp'),
                dl.GeoJSON(data=geojson, options=dict(pointToLayer=ns('draw_icon')),id='geojson'),
                dl.Minichart(lat=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['centre_coords'].values[0][0], 
                             lon=survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['centre_coords'].values[0][1], 
                             type="bar", 
                             maxValues = 100,
                             colors=["blue"],
                             height=200,
                             labels=["medium"],
                             id="bar_mini_0"),
                dl.Minichart(lat=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['centre_coords'].values[0][0], 
                             lon=survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['centre_coords'].values[0][1],
                             type="bar",  
                             maxValues = 100,
                             colors=["green"],
                             height=200,
                             labels=["high"],
                             id="bar_mini_1"),
                info,
                trito_logo])]


#Create app layout 
app.layout = html.Div([
dl.Map(style={'width': '95vw', 'height': '98vh','margin': '30px'},
            center=map_centre_coords,
            zoom=start_zoom,
            maxZoom=1000,
            id = "map",
            children=initial_map_children),
dcc.Store(id = 'intermediate_mapview'),
dcc.Store(id = 'survey_marker_click_intermediate'),
dcc.Store(id = 'serp_marker_click_intermediate'),
dcc.Store(id = 'intermediate_marker_hover'),
dcc.Store(id = 'mini_chart_0_intermediate'),
dcc.Store(id = 'mini_chart_1_intermediate')])

@app.callback(
              Output('intermediate_mapview','data'),
              Output("map", "viewport"),
              Output("info",'children'),
              Output('survey_marker_click_intermediate','data'),
              Output('serp_marker_click_intermediate','data'),
              Output('intermediate_marker_hover','data'),
              Output('mini_chart_0_intermediate','data'),
              Output('mini_chart_1_intermediate','data'),
              Input("map", "viewport"),
              Input('intermediate_mapview','data'),
              Input('geojson', 'n_clicks'),
              Input('survey_marker_click_intermediate','data'),
              Input('geojson_serp', 'n_clicks'),
              Input('serp_marker_click_intermediate','data'),
              Input('geojson', 'hover_feature'),
              Input('geojson_serp', 'hover_feature'),
              Input('intermediate_marker_hover','data')
              )

def update_map_and_graphics(map_view,
                            intermediate_mapview,
                            marker_clicks_0,
                            intermediate_clicks_0,
                            marker_clicks_serp,
                            intermediate_clicks_serp,
                            marker_hover,
                            marker_hover_serp,
                            intermediate_marker_hover):
   
    ctx = callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # some really crude ways to deal with null cases
    if map_view is None:
          map_view = {'center': [56.58215811323581, -5.701866236751068]}

    if not marker_hover:
        marker_hover =  {'properties': {'name': '123'}}

    if not marker_hover_serp:
        marker_hover_serp =  {'properties': {'name': '123'}}



    # currently just a hard wired list of each survey names in if statements must be changed to iterate over all surveys
    if (survey_df.loc[survey_df['species_name'] == marker_hover['properties']['name']]['survey_dash_id'].values == 'ard_bay_2022' or marker_hover['properties']['name'] == '123') and  marker_clicks_0 !=  intermediate_clicks_0  :
        set_map_view(map_view,'ard_bay_2022',survey_df)
        mini_chart_0_intermediate = [0]                
        mini_chart_1_intermediate = [0]
        info_out = write_info_out('',survey_df)

    elif(survey_df.loc[survey_df['species_name'] == marker_hover['properties']['name']]['survey_dash_id'].values == 'ard_bay_2022' ) and input_id == 'geojson':
        mini_chart_0_intermediate = [survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['nat_cap_number'].values[0] ] 
        mini_chart_1_intermediate = [0]
        info_out = write_info_out('ard_bay_2022',survey_df)
    
    elif (survey_df.loc[survey_df['species_name'] == marker_hover['properties']['name']]['survey_dash_id'].values == 'creran_2023' or marker_hover['properties']['name'] == '123') and  marker_clicks_0 !=  intermediate_clicks_0  :
        set_map_view(map_view,'creran_2023',survey_df)
        mini_chart_0_intermediate = [0]                
        mini_chart_1_intermediate = [0]
        info_out = write_info_out('',survey_df)

    elif(survey_df.loc[survey_df['species_name'] == marker_hover['properties']['name']]['survey_dash_id'].values == 'creran_2023' or marker_hover['properties']['name'] == '123') and marker_clicks_serp !=  intermediate_clicks_serp :
        set_map_view(map_view,'creran_2023',survey_df)
        mini_chart_0_intermediate = [0]                
        mini_chart_1_intermediate = [0]
        info_out = write_info_out('',survey_df)

    elif(survey_df.loc[survey_df['species_name'] == marker_hover['properties']['name']]['survey_dash_id'].values == 'creran_2023' ) and input_id == 'geojson':
            mini_chart_0_intermediate = [0]                
            mini_chart_1_intermediate = [survey_df.loc[survey_df['survey_dash_id'] == 'creran_2023']['nat_cap_number'].values[0] ]
            info_out = write_info_out('creran_2023',survey_df)

    else:
        mini_chart_0_intermediate = [0]                
        mini_chart_1_intermediate = [0]
        info_out = write_info_out('',survey_df)
    
    # save marker clicks to intermediate variable for use in call back called not on marker click
    if marker_clicks_0:
        intermediate_clicks_0 =  marker_clicks_0

    if marker_clicks_serp:
        intermediate_clicks_serp =  marker_clicks_serp
  

    return   intermediate_mapview, map_view, info_out,  intermediate_clicks_0, intermediate_clicks_serp, intermediate_marker_hover  ,mini_chart_0_intermediate ,mini_chart_1_intermediate


# Javascript callback for minichart animation
app.clientside_callback("""
function(mini_chart_0_intermediate ,mini_chart_1_intermediate){
    const fakeData1 = () => mini_chart_0_intermediate
    const fakeData2 = () => mini_chart_1_intermediate 
    return [fakeData1(), fakeData2()]
}
""", [Output("bar_mini_0", "data")], [Output("bar_mini_1", "data")], [Input("mini_chart_0_intermediate", "data"),Input("mini_chart_1_intermediate", "data")])


if __name__ == '__main__':
    app.run_server(debug=True,port=8053)
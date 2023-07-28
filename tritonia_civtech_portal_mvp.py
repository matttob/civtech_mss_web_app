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
import geopandas as gpd
import fiona
from shapely.geometry import shape, GeometryCollection, Point
fiona.drvsupport.supported_drivers['KML'] = 'rw'
ns = Namespace('dashExtensions','dashExtensionssub')

# Images
logo_image_path = 'assets/Logo2.png'

# meta_data
survey_list_file_path = 'all_survey_list.json'

def load_meta_data(config_file_path):
    f = open(config_file_path)
    survey_json_paths = json.load(f)['survey_json_paths']
    # load all jsons could maybe load on demand in future
    survey_json_list = []
    for  survey in survey_json_paths:
        with open(survey, 'r') as openfile:
            survey_json = json.load(openfile)
        survey_json_list.append(survey_json)
    survey_df = pd.DataFrame.from_dict(survey_json_list)
    return survey_df

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
    map_view['zoom'] = 23
    return map_view

def write_info_out(survey_dash_id,survey_df):
    survey_data = survey_df.loc[survey_df['survey_dash_id'] == survey_dash_id]
    if  (len(survey_data['species_m2'].values)) > 0:
        info_out = ("** Survey Name** : " +  str(survey_data['survey_long_name'].values[0]) + " \n" + " \n" +
                "**Species Present** : " + str(survey_data['species_name'].values[0]) + " \n" + " \n" +
                "**Total Area of Species : **" + (str(survey_data['species_m2'].values[0]))+ " \n" + " \n" +
                "**Number of Individuals : **" + str(survey_data['number_of_individuals'].values[0]) + " \n" + " \n" )
    else:
            info_out = ("** Survey Name** : " + " \n" + " \n" +
                    "**Species Present** : "  + " \n" + " \n" +
                    "**Total Area of Species : **"  + " \n" + " \n" +
                    "**Number of Individuals : **"  + " \n" + " \n" )
    return info_out

def write_info_aggregate_out(survey_df):
    info_agg_out = ("**Species Present**"  + " \n" + " \n" )
    survey_df_filt_area= survey_df.groupby('species_name')['species_m2'].sum().to_frame()
    survey_df_filt_individuals = survey_df.groupby('species_name')['number_of_individuals'].sum().to_frame()
    for n in survey_df_filt_area.index:
        if type(survey_df_filt_area.loc[n]['species_m2']) == float:
            info = (n  + "  :  " + str('{0:.2f}'.format(survey_df_filt_area.loc[n]['species_m2']))+ " (m2)"" \n" + " \n" )
            info_agg_out = info_agg_out + info
    for n in survey_df_filt_individuals.index:
        if type(survey_df_filt_individuals.loc[n]['number_of_individuals']) == int:
            info = (n  + "  :  " + str(survey_df_filt_individuals.loc[n]['number_of_individuals'])+ " (Individuals)"" \n" + " \n" )
            info_agg_out = info_agg_out + info
    return info_agg_out

def create_survey_markers(survey_df):
    survey_markers_dicts= []
    for n in range(len(survey_df)):
        survey_marker_dict = dict(name=survey_df['survey_long_name'][n],
                        iso2=survey_df['marker_type'][n],
                        marker_size = 48,
                        lat=survey_df['centre_coords'][n][0],
                        lon=survey_df['centre_coords'][n][1])
        survey_markers_dicts.append(survey_marker_dict)
    survey_markers_geojson = dlx.dicts_to_geojson([{**c, **dict(tooltip=c['name'])} for c in survey_markers_dicts])
    return survey_markers_geojson

# create survey meta data dataframe
survey_df = load_meta_data(survey_list_file_path)

# create survey location markers
survey_markers_geojson = create_survey_markers(survey_df)

# create dash app
app = Dash(__name__)

#create the info panel where text can be displayed
info = html.Div(dcc.Markdown(id="info", className="info",
                style={"position": "absolute", "bottom": "550px", "right": "80px", "z-index": "1000", 'width':'270px'}),id ='info_vis',style = {'display': 'none'})

info_aggregate = html.Div(dcc.Markdown(id="info_aggregate", className="info_aggregate",),id ='info_aggregate_vis',
                          style = {"z-index": "999",'width':'200px','height':'50px',"position": "absolute", "top": "250px", "left": "120px",'background-color': 'white','border-radius': '10px','opacity': '0.9','visibility':'hidden'})

species_time_series_df_initial_counts = [survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2022']['species_m2'].values[0],
                                         survey_df.loc[survey_df['survey_dash_id'] == 'ard_bay_2023']['species_m2'].values[0]]
species_time_series_df_initial_years = [2022,2023]
species_time_series_df_initial = pd.DataFrame(list(zip(species_time_series_df_initial_years, species_time_series_df_initial_counts)),
               columns =['year', 'pixel_area_count'])

species_time_series_plot = px.line(species_time_series_df_initial,x='year',y='pixel_area_count',
                                    range_x=[2021, 2024],
                                    range_y=[0, 4],
                                     markers = True)
species_time_series_plot.update_traces(line = dict(width = 4, color = "DeepSkyBlue"),
                  marker = dict(color = "DeepSkyBlue", size = 15))

species_time_series_plot.layout.autosize = False
species_time_series_plot.layout.width = 380
species_time_series_plot.layout.height = 500

species_time_series_plot.update_layout(
    xaxis = dict(
        tickmode = 'array',
        tickvals = [2021,2022,2023,2024],
        ticktext = ['2021', '2022', '2023','2024'],
        showgrid=True),
        plot_bgcolor = 'lightgrey',
        paper_bgcolor='rgba(0,0,0,0)',
         yaxis=dict(showgrid=True),
         yaxis_title= "Species Coverage Area (m<sup>2</sup>)",
         xaxis_title= "Year")

species_select_div =  html.Div(id="species_select_div", className="species_select_div",children=[
                html.Label(['Filter by species:'], style={'font-weight': 'bold', "text-align": "center"}),
                dcc.Dropdown(id = 'species_select',
                        options=['all']+list(set(list(survey_df['species_name']))),
                        value='all',  # initial value displayed when page first loads
                        clearable=False)],
                        style={'width':'200px',"z-index": "1000","position": "absolute", "top": "100px", "left": "120px"})

trito_logo = html.Div(id="trito_logo", className="trito_logo",
                      style={"position": "absolute", "bottom": "40px", "left": "10px", "z-index": "1000"},
                      children = [html.Img(src=logo_image_path,style={'height':'10%', 'width':'10%'})])

base_layer_list = [
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",id="TileMap")),name="BaseMap",checked=False),
                                dl.Overlay(dl.LayerGroup(dl.TileLayer()),name="Map Labels",checked=True),
                dl.LayerGroup(id="layer"),
                dl.Overlay(dl.GeoJSON(data=survey_markers_geojson, options=dict(pointToLayer=ns('draw_icon')),id='survey_markers_geojson'),name = 'Survey Markers',checked=True),
                info,
                info_aggregate,
                trito_logo,
                dl.FeatureGroup([dl.ScaleControl(id="scale")]),
                dl.FeatureGroup([dl.EditControl(id="edit_control")])
                ]
map_children_iniital=[dl.LayersControl(base_layer_list[:])]

# Set map default view
start_zoom = 10
map_centre_coords = [56.5314423498172, -5.619001454153479]

#Create app layout
app.layout = html.Div([
dl.Map(style={'width': '95vw', 'height': '98vh','margin': '15px'},
            center=map_centre_coords,
            zoom=start_zoom,
            maxZoom=1000,
            id = "map",
            children=map_children_iniital),
dcc.Store(id = 'intermediate_mapview'),
dcc.Store(id = 'intermediate_marker_hover'),
species_select_div,

html.Div(html.Div([dcc.RangeSlider(
id='date_select_slide',
min=2017,
max=2023,
value=[2023],
step=1,
marks={
        2017: '2017',
        2018: '2018',
        2019: '2019',
        2020: '2020',
        2021: '2021',
        2022: '2022',
        2023: '2023'
    },
    verticalHeight = 10,
)], style={"z-index": "999",'width':'300px','height':'35px',"position": "absolute", "top": "10px", "left": "0px",'background-color': 'white','border-radius': '10px','opacity': '0.9'}),
    style={"z-index": "999",'width':'300px','height':'50px',"position": "absolute", "top": "40px", "left": "120px",'background-color': 'white','border-radius': '10px','opacity': '0.9'}),

html.Div([
    dcc.Graph(
        id='time_series_plot',
        figure=species_time_series_plot
    )],id='time_series_plot_div',style={"position": "absolute", "bottom": "30px", "right": "60px", "z-index": "1000",
                                        'width':'350px','background-color': 'white','visibility': 'hidden','border-radius': '10px','opacity': '0.9','padding':'1px'}),
])

@app.callback(
              Output('intermediate_mapview','data'),
              Output("map", "viewport"),
              Output("map", "children"),
              Output("info",'children'),
              Output("info_vis",'style'),
              Output("info_aggregate",'children'),
              Output("info_aggregate_vis",'style'),
              Output('intermediate_marker_hover','data'),
              Output('survey_markers_geojson', 'data'),
              Output('time_series_plot_div','style'),
              Input("map", "viewport"),
              Input('intermediate_mapview','data'),
              Input('survey_markers_geojson', 'n_clicks'),
              Input('survey_markers_geojson', 'hover_feature'),
              Input('intermediate_marker_hover','data'),
              Input('species_select_div',"style"),
              Input('species_select','value'),
              Input('date_select_slide','value'),
              Input('time_series_plot_div','style'),
              Input("edit_control", "geojson"),
              )

def update_map_and_graphics(map_view,
                            intermediate_mapview,
                            marker_clicks_0,
                            marker_hover,
                            intermediate_marker_hover,
                            species_filter_div,
                            species_filter,
                            survey_year,
                            time_series_plot_div_style,
                            edit_control_polygon_json):

    # some really crude ways to deal with null cases
    if map_view is None:
          map_view = {'center': [56.58215811323581, -5.701866236751068]}

    if not marker_hover:
        marker_hover =  {'properties': {'name': '123'}}

    if not marker_clicks_0:
        marker_clicks_0 = 0

    # filter survey dataframe on year then species
    survey_df_species_filt = survey_df.copy()
    survey_df_species_filt = survey_df_species_filt[survey_df_species_filt['survey_date'] == str(survey_year[0]) ]
    if species_filter != 'all':
        survey_df_species_filt = survey_df_species_filt[survey_df_species_filt['species_name'] == str(species_filter) ]

    # filter species dataframe based on polygon selection
    if edit_control_polygon_json:
        if len(edit_control_polygon_json['features'])>0:
            print(edit_control_polygon_json['features'])
            survey_df_poly = survey_df_species_filt.copy()
            for n in survey_df_poly.index:
                for feature in edit_control_polygon_json['features']:
                    polygon = shape(feature['geometry'])
                    if not (Point(survey_df['centre_coords'][n][1],survey_df['centre_coords'][n][0])).within(polygon):
                        survey_df_poly = survey_df_poly.drop(n)
            info_aggregate_out = write_info_aggregate_out(survey_df_poly)
            info_aggregate_style ={"z-index": "999",'width':'200px','height':'200px',"position": "absolute", "top": "350px", "left": "10px",'background-color': 'white','border-radius': '10px','opacity': '0.9','visibility':'visible'}
        else:
            info_aggregate_out = ''
            info_aggregate_style = {"z-index": "999",'width':'300px','height':'200px',"position": "absolute", "top": "350px", "left": "10px",'background-color': 'white','border-radius': '10px','opacity': '0.9','visibility':'hidden'}
    else:
        info_aggregate_out = ''
        info_aggregate_style = {"z-index": "999",'width':'200px','height':'200px',"position": "absolute", "top": "350px", "left": "10px",'background-color': 'white','border-radius': '10px','opacity': '0.9','visibility':'hidden'}

    # create layers for photogrametty orhtos and species polygons
    layer_level = 0
    map_layer_list = base_layer_list.copy()
    survey_map_overlay_layer= []
    for n in survey_df_species_filt.index:
        survey_map_overlay_layer = dl.Overlay(dl.LayerGroup(dl.TileLayer(url=create_marble_cutter_tile(survey_df_species_filt['COG_ARN'][n])['tiles'][0],
                        id= survey_df_species_filt['survey_dash_id'][n])),
                        name=survey_df_species_filt['survey_long_name'][n],checked=True)
        map_layer_list.insert(layer_level+len(base_layer_list),survey_map_overlay_layer)
        if  len(survey_df_species_filt['species_polygons'][n])>1:
            if survey_df_species_filt['species_polygons'][n]['features'][0]['geometry']['type'] == 'Polygon':
                species_poly_map_overlay_layer = dl.Overlay(dl.GeoJSON(data=survey_df_species_filt['species_polygons'][n] , id=  survey_df_species_filt['survey_dash_id'][n] + '_species' ),name = survey_df_species_filt['survey_long_name'][n]+'species',checked=True)
                map_layer_list.insert(layer_level+1+len(base_layer_list), species_poly_map_overlay_layer)
                layer_level += 2
            elif survey_df_species_filt['species_polygons'][n]['features'][0]['geometry']['type'] == 'Point':
                for ii in range(0,len(survey_df_species_filt['species_polygons'][n]['features'])):
                    survey_df_species_filt['species_polygons'][n]['features'][ii]['properties']['iso2'] = 'serp_individual'
                    survey_df_species_filt['species_polygons'][n]['features'][ii]['properties']['marker_size'] = 20
                species_poly_map_overlay_layer = dl.GeoJSON(data=survey_df_species_filt['species_polygons'][n],options=dict(pointToLayer=ns('draw_icon')),id=survey_df_species_filt['survey_dash_id'][n])
                map_layer_list.insert(layer_level+1+len(base_layer_list), species_poly_map_overlay_layer)
                layer_level += 2

    # create layers for survery location markers
    # Survey position markers
    survey_markers_dicts= []
    for n in survey_df_species_filt.index:
        survey_marker_dict = dict(name=survey_df_species_filt['survey_long_name'][n],
                        iso2=survey_df_species_filt['marker_type'][n],
                        marker_size = 48,
                        lat=survey_df_species_filt['centre_coords'][n][0],
                        lon=survey_df_species_filt['centre_coords'][n][1])
        survey_markers_dicts.append(survey_marker_dict)
    survery_marker_data = dlx.dicts_to_geojson([{**c, **dict(tooltip=c['name'])} for c in survey_markers_dicts])

    map_children_out=[dl.LayersControl(map_layer_list[:])]

    ctx = callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if len(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values) > 0 :
        # currently just a hard wired list of each survey names in if statements must be changed to iterate over all surveys
        if survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'ard_bay_2023' and  marker_clicks_0 > 0   :
            set_map_view(map_view,'ard_bay_2023',survey_df)
            info_out = write_info_out('ard_bay_2023',survey_df)
            info_style= {'display': 'block'}
            time_series_plot_div_style =  {"position": "absolute", "bottom": "30px", "right": "60px", "z-index": "1000",
                                            'width':'350px','background-color': 'white','visibility': 'visible','border-radius': '10px','opacity': '0.9','padding':'1px'}

        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'ard_bay_2023' ) and input_id == 'survey_markers_geojson':
            print('test')
            info_out = write_info_out('ard_bay_2023',survey_df)
            info_style= {'display': 'block'}
            time_series_plot_div_style =  {"position": "absolute", "bottom": "30px", "right": "60px", "z-index": "1000",
                                            'width':'350px','background-color': 'white','visibility': 'visible','border-radius': '10px','opacity': '0.9','padding':'1px'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'ard_bay_2022' and  marker_clicks_0 > 0   :
            set_map_view(map_view,'ard_bay_2022',survey_df)
            info_out = write_info_out('ard_bay_2022',survey_df)
            info_style= {'display': 'block'}
            time_series_plot_div_style =  {"position": "absolute", "bottom": "30px", "right": "60px", "z-index": "1000",
                                            'width':'350px','background-color': 'white','visibility': 'visible','border-radius': '10px','opacity': '0.9','padding':'1px'}

        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'ard_bay_2022' ) and input_id == 'survey_markers_geojson':
            info_out = write_info_out('ard_bay_2022',survey_df)
            info_style= {'display': 'block'}
            time_series_plot_div_style =  {"position": "absolute", "bottom": "30px", "right": "60px", "z-index": "1000",
                                            'width':'350px','background-color': 'white','visibility': 'visible','border-radius': '10px','opacity': '0.9','padding':'1px'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'creran_2023'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'creran_2023',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}
        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'creran_2023' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('creran_2023',survey_df)
                info_style= {'display': 'block'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'creran_T1_15_03_2023'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'creran_2023',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}

        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'creran_T1_15_03_2023' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('creran_T1_15_03_2023',survey_df)
                info_style= {'display': 'block'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'CentralCreagan_HorseMussels_2023'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'CentralCreagan_HorseMussels_2023',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}
        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'CentralCreagan_HorseMussels_2023' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('CentralCreagan_HorseMussels_2023',survey_df)
                info_style= {'display': 'block'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'Creagan_Bridge_HorseMussels_2023'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'Creagan_Bridge_HorseMussels_2023',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}
        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'Creagan_Bridge_HorseMussels_2023' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('Creagan_Bridge_HorseMussels_2023',survey_df)
                info_style= {'display': 'block'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'BN17'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'BN17',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}
        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'BN17' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('BN17',survey_df)
                info_style= {'display': 'block'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'BN18'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'BN18',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}
        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'BN18' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('BN18',survey_df)
                info_style= {'display': 'block'}

        elif survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'BN19'  and  marker_clicks_0 > 0   :
            set_map_view(map_view,'BN19',survey_df)
            info_out = write_info_out('',survey_df)
            info_style= {'display': 'block'}
        elif(survey_df.loc[survey_df['survey_long_name'] == marker_hover['properties']['name']]['survey_dash_id'].values[0] == 'BN19' ) and input_id == 'survey_markers_geojson':
                info_out = write_info_out('BN19',survey_df)
                info_style= {'display': 'block'}

    else:
            info_out = write_info_out('',survey_df)
            info_style = {'display': 'none'}
            time_series_plot_div_style =  {"position": "absolute", "bottom": "30px", "right": "60px", "z-index": "1000",
                                            'width':'350px','background-color': 'white','visibility': 'hidden','border-radius': '10px','opacity': '0.9','padding':'1px'}

    return   intermediate_mapview, map_view,map_children_out, info_out, info_style,info_aggregate_out, info_aggregate_style, intermediate_marker_hover , survery_marker_data , time_series_plot_div_style

if __name__ == '__main__':
    app.run_server(debug=True,port=8052)
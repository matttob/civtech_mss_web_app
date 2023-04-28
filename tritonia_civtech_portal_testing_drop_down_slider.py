#Import PLotly Dash , Dash Leaflet (for mapping), Jupyter Dash (for using dash/dash leaflet in notebook),
# Import  Json & httpx for getting data from TiTiler 
from dash import Dash, html,dcc,Input, Output
import dash_leaflet as dl
import json
import httpx
import numpy as np
import random
from dash_extensions.javascript import assign
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
from osgeo import gdal
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


# Enter tiler details
# titiler_endpoint= "https://os8ci3nx02.execute-api.eu-west-2.amazonaws.com"  # titiler docker image running on local .
titiler_endpoint= "https://os8ci3nx02.execute-api.eu-west-2.amazonaws.com"  # titiler docker image running on local .

# survey locations
survey_location_list = ['none','Ardmucknish Bay 2023','Ardmucknish Bay 2022','Loch Creran NMPI T1', 'Loch Creran Serpulids']

# hack to find pixel area in future this shoudl be specific for each data set
dataset = gdal.Open('/Users/matthewtoberman/Downloads/CRACK_ID_blue_flipped_downsample_metres.tif') 
got = dataset.GetGeoTransform()
pixel_area = abs(got[1]*got[5])

# Style and Images
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
logo_image_path = 'assets/Logo2.png'


def get_centre_geotiff(url):
    bounded_data = httpx.get(
    f"{titiler_endpoint}/cog/bounds",
    params = {
        "url": url,
        }
    ).json()
    center_lon = (bounded_data['bounds'][2]+bounded_data['bounds'][0])/2
    center_lat = (bounded_data['bounds'][1]+bounded_data['bounds'][3])/2
    centre_coords = [center_lon,center_lat]
    return centre_coords


def whole_geotiff_polygon(url):
    bounded_data = httpx.get(
    f"{titiler_endpoint}/cog/bounds",
    params = {
        "url": url,
        }
    ).json()
    entire_geotiff_poly = Polygon([[bounded_data['bounds'][0],bounded_data['bounds'][1]],
                      [bounded_data['bounds'][2],bounded_data['bounds'][1]],
                      [bounded_data['bounds'][2],bounded_data['bounds'][3]],
                      [bounded_data['bounds'][0],bounded_data['bounds'][3]]])
    return entire_geotiff_poly


def update_species_plots(species_df):
    species_bar = px.bar(species_df[species_df['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
                            color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
                            labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (Testing) '},
                            range_y=[0, 20])
    species_bar.update_layout(
    showlegend=False,
    xaxis = dict(
        showgrid=False),
    yaxis=dict(showgrid=False),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")

    return species_bar

def update_species_time_plots(species_time_series_df):
    species_time_series_plot = px.line(species_time_series_df,x='year',y='pixel_area_count',
                                range_x=[2021,2024],
                                range_y=[0, 20],
                                labels={'year': 'Year','pixel_area_count': 'Area Covered  (Testing) '})

    species_time_series_plot.update_layout(
            xaxis = dict(
                tickmode = 'array',
                tickvals = [2021,2022,2023,2024],
                ticktext = ['2021', '2022', '2023', '2024'],
                showgrid=False),
                yaxis=dict(showgrid=False),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")
    
    return species_time_series_plot


def update_sepcies_df(id_geotiff_path,polygon):
    # count pixels of species ID at the moment the file name is supplied here but should be some sort of tuple with the no species ID image file
    with rasterio.open(id_geotiff_path) as src:
        pink_out_image, out_transform = rasterio.mask.mask(src,[polygon], crop=True,pad=True,nodata=99)
    pink_non_zero_alpha_band_count = ((pink_out_image[3,:,:] ==  255)).sum()
   
    # count no species coloured pixels
    no_species_count = ((pink_out_image[3,:,:] != 99)).sum()-((pink_out_image[3,:,:] ==  255)).sum()

    # create data frame for species plots
    species_df = pd.DataFrame(['pink'],columns=['Species'])
    species_df['Pixel Count'] = pink_non_zero_alpha_band_count
    species_df['coverage_sqm']= pink_non_zero_alpha_band_count*pixel_area
    species_df.loc[len(species_df)] = ['blue',0,0] 
    species_df.loc[len(species_df)] = ['none',no_species_count,0] 
    return species_df


ard_bay_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_ROV_20_10_2_5mmPix_wgs84_test_Georeferenced_clipped.tif"
ard_bay_request = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": ard_bay_url,
        "rescale": f"{0},{255}",
    }
).json()
ard_bay_center_coords  = get_centre_geotiff(ard_bay_url)
ard_bay_marker = dl.Marker(id='ard_bay_marker', position=(ard_bay_center_coords[1], ard_bay_center_coords[0]))


pink_t0_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_CRACK_ID_pink_downsample.tif"
request_pink_t0= httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": pink_t0_url,
        "rescale": f"{0},{255}",
    }
).json()


ard_bay_diver_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_crack_diverModel_Orthomosaic.tif"
ard_bay_diver_request = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": ard_bay_diver_url,
        "rescale": f"{0},{255}",
    }
).json()
ard_bay_whole_geotiff_polygon = whole_geotiff_polygon(ard_bay_url)

ard_bay_diver_pink_t0_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_crack_species_only_Orthomosaic_downsample.tif"
ard_bay_diver_request_pink_t0= httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": ard_bay_diver_pink_t0_url,
        "rescale": f"{0},{255}",
    }
).json()


Creran_15_03_23_T1_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_Creran_15_03_23_T1.tif"
Creran_15_03_23_T1_request = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": Creran_15_03_23_T1_url,
        "rescale": f"{0},{255}",
    }
).json()
Creran_15_03_23_T1_center_coords  = get_centre_geotiff("https://tiletesting.s3.eu-west-2.amazonaws.com/COG_Creran_15_03_23_T1.tif")
Creran_15_03_23_T1_marker = dl.Marker(id='Creran_15_03_23_T1_marker', position=(Creran_15_03_23_T1_center_coords[1], Creran_15_03_23_T1_center_coords[0]))


Creran_serp_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_CrereanSerpOrthoCropped.tif"
Creran_serp_request = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": Creran_serp_url,
        "rescale": f"{0},{255}",
    }
).json()

Creran_serp_ID_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_CreranSerpClassified_downsample.tif"
Creran_serp_ID_request = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": Creran_serp_ID_url,
        "rescale": f"{0},{255}",
    }
).json()
Creran_serp_center_coords  = get_centre_geotiff("https://tiletesting.s3.eu-west-2.amazonaws.com/COG_CrereanSerpOrthoCropped.tif")
Creran_serp_marker = dl.Marker(id='Creran_serp_marker', position=(Creran_serp_center_coords[1], Creran_serp_center_coords[0]))


# Initialise species ID data frames
species_df_initial = pd.DataFrame(['pink'],columns=['Species'])
species_df_initial['Pixel Count'] = 0
species_df_initial['coverage_sqm']= 0
species_df_initial.loc[len(species_df_initial)] = ['blue',0,0] 
species_df_initial.loc[len(species_df_initial)] = ['none',1,1] 
species_time_series_df_initial_counts = [0]
species_time_series_df_initial_years = [2022,2023]
species_time_series_df_initial = pd.DataFrame(list(zip(species_time_series_df_initial_years, species_time_series_df_initial_counts)),
               columns =['year', 'pixel_area_count'])


# Initialise species ID plots
species_bar = px.bar(species_df_initial[species_df_initial['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
                     color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
                     labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (Testing) '},
                     range_y=[0, 8])
species_bar.update_layout(
     showlegend=False,
    xaxis = dict(
        showgrid=False),
         yaxis=dict(showgrid=False),
         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")


species_time_series_plot = px.line(species_time_series_df_initial,x='year',y='pixel_area_count',
                                    range_x=[2020, 2022],
                                    range_y=[0, 8],
                                    labels={'year': 'Year','pixel_area_count': 'Area Covered  (Testing) '})
species_time_series_plot.update_layout(
    xaxis = dict(
        tickmode = 'array',
        tickvals = [2020,2021,2022],
        ticktext = ['2020', '2021', '2022'],
        showgrid=False),
         yaxis=dict(showgrid=False),
         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white")

marker_count = 0 


# create dash app
app = Dash(__name__)

#create the info panel where text can be displayed
info = html.Div( id="info", className="info",
                style={"position": "absolute", "bottom": "10px", "left": "10px", "z-index": "1000"})

plots = html.Div(id="plots", className="plots",style={"position": "absolute", "bottom": "10px", "right": "10px", "z-index": "1000"},children = [
dcc.Graph(id='species_bar',
            figure=species_bar,style={'width': '300px', 'height': '300px','float': 'left','margin': '1px'}),
dcc.Graph(id='species_time_series_plot',
            figure=species_time_series_plot,style={'width': '300px', 'height': '300px','float': 'left','margin': '1px'})])

trito_logo = html.Div(id="trito_logo", className="trito_logo",
                      style={"position": "absolute", "bottom": "50px", "left": "10px", "z-index": "1000"},
                      children = [html.Img(src=logo_image_path,style={'height':'10%', 'width':'10%'})])

# Set map default view
start_zoom = 8
map_centre_coords = [56.5314423498172, -5.619001454153479]
initial_map_children=[ 
                dl.LayersControl([
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_request["tiles"][0],id="Ardmicknish_bay_2023")),name="Ardmicknish_bay_2023",checked=True),
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_pink_t0["tiles"][0], opacity=0.4,id="Ardmicknish_bay_2023_ID")),name="Ardmicknish_bay_2023_ID",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Creran_15_03_23")),name="Creran_15_03_23",checked=True),       
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_serp_request["tiles"][0],id="Creran Serpulids")),name="Creran Serpulids",checked=True),       
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_serp_ID_request["tiles"][0],opacity=0.4,id="Creran Serpulids ID")),name="Creran Serpulids ID",checked=True),  
                
                dl.LayerGroup(id="layer"),
                plots,
                info,
                trito_logo]),
                ard_bay_marker,
                Creran_15_03_23_T1_marker,
                Creran_serp_marker
                ]



#Create app layout 
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
                        options=survey_location_list,
                        value='none',  # initial value displayed when page first loads
                        clearable=False)],
                        style=dict(width='25%')),
html.Div([dcc.RangeSlider(
id='date_select_slide',
min=2022,
max=2023,
value=[2023],
step=1,
marks={
        2022: '2022',
        2023: '2023'
    },
)], style= {'width': '500px','float': 'left','margin': '60px'}),
dcc.Store(id = 'intermediate_mapview'),
dcc.Store(id = 'intermediate_ard_bay_click'),
dcc.Store(id = 'intermediate_Creran_15_03_23_T1_clicks'),
dcc.Store(id = 'intermediate_Creran_serp_clicks') 
])



@app.callback(Output("species_bar",component_property='figure'),
              Output("species_time_series_plot",component_property='figure'),
              Output('intermediate_mapview','data'),
              Output("survery_select", component_property='value'),
              Output("map", "viewport"),
              Output("info",component_property='children'),
              Output('intermediate_ard_bay_click','data'),
              Output('intermediate_Creran_15_03_23_T1_clicks','data'),
              Output('intermediate_Creran_serp_clicks','data'),
              Output("map", "children"),
              Input("map", "viewport"),
              Input("survery_select", component_property='value'),
              Input('intermediate_mapview','data'),
              Input('ard_bay_marker', 'n_clicks'),
              Input('intermediate_ard_bay_click','data'),
              Input('Creran_15_03_23_T1_marker', 'n_clicks'),
              Input('intermediate_Creran_15_03_23_T1_clicks','data'),
              Input('Creran_serp_marker', 'n_clicks'),
              Input('intermediate_Creran_serp_clicks','data'),
              Input("date_select_slide","value"),
              )

def count_species_cover_in_polygon(map_view,survey_name,intermediate_mapview,ard_bay_marker_clicks,
                                   intermediate_ard_bay_click,Creran_15_03_23_T1_clicks,intermediate_Creran_15_03_23_T1_clicks,
                                   Creran_serp_clicks,intermediate_Creran_serp_clicks,date_select_slide_value):
    
    
    # update info box with file name used for slider values
    info_out = str(survey_name)

    # for some reason 1st time page loads there is no input from app from map:viewport
    if map_view is None:
          map_view = {'center': [56.58215811323581, -5.701866236751068], 'zoom': 9}
          map_children=initial_map_children

    # If statements for each case of the dropdown menu - 
    # this must be improved also at present the entire child of the map is being changed even 
    # though in most cases there are some layers that are not being updated
    if survey_name == 'Ardmucknish Bay 2023' or ard_bay_marker_clicks!= intermediate_ard_bay_click  :
        map_view['center'] =  [ard_bay_center_coords[1],ard_bay_center_coords[0]]
        map_view['zoom'] = 20
        
        print(date_select_slide_value[0])
        if date_select_slide_value[0] == 2023:
            map_children_slide =  [ 
                dl.LayersControl([
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_request["tiles"][0],id="Ardmicknish_bay_2023")),name="Ardmicknish_bay_2023",checked=True),
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_pink_t0["tiles"][0], opacity=0.4,id="Ardmicknish_bay_2023_ID")),name="Ardmicknish_bay_2023_ID",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Creran_15_03_23")),name="Creran_15_03_23",checked=True),       
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_serp_request["tiles"][0],id="Creran Serpulids")),name="Creran Serpulids",checked=True),       
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_serp_ID_request["tiles"][0],opacity=0.4,id="Creran Serpulids ID")),name="Creran Serpulids ID",checked=True),  
                
                dl.LayerGroup(id="layer"),
                plots,
                info,
                trito_logo]),
                ard_bay_marker,
                Creran_15_03_23_T1_marker,
                Creran_serp_marker
                ]
        else:
            print('test')
            map_children_slide = [ 
                dl.LayersControl([
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_diver_request["tiles"][0],id="Ardmicknish_bay_2022")),name="Ardmicknish_bay_2022",checked=True),       
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_diver_request_pink_t0["tiles"][0],opacity=0.4,id="Ardmicknish_bay_2022_ID")),name="Ardmicknish_bay_2022_ID",checked=True),  
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Creran_15_03_23")),name="Creran_15_03_23",checked=True),       
                
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_serp_request["tiles"][0],id="Creran Serpulids")),name="Creran Serpulids",checked=True),       
                dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_serp_ID_request["tiles"][0],opacity=0.4,id="Creran Serpulids ID")),name="Creran Serpulids ID",checked=True),  
                
                dl.LayerGroup(id="layer"),
                plots,
                info,
                trito_logo]),
                ard_bay_marker,
                Creran_15_03_23_T1_marker,
                Creran_serp_marker
                ]



        species_df = update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/CRACK_ID_pink_downsample.tif',whole_geotiff_polygon(ard_bay_url))
        species_bar = update_species_plots(species_df)
        
        species_time_series_counts = [update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/crack_species_only_Orthomosaic_downsample.tif',whole_geotiff_polygon(ard_bay_diver_url))['coverage_sqm'][0],
        update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/CRACK_ID_pink_downsample.tif',whole_geotiff_polygon(ard_bay_url))['coverage_sqm'][0]]
        species_time_series_years = [2022,2023]
        species_time_series_df = pd.DataFrame(list(zip(species_time_series_years, species_time_series_counts)),
               columns =['year', 'pixel_area_count'])
        species_time_series_plot = update_species_time_plots(species_time_series_df)



    if survey_name == 'Ardmucknish Bay 2022' or ard_bay_marker_clicks!= intermediate_ard_bay_click :
        map_view['center'] =  [ard_bay_center_coords[1],ard_bay_center_coords[0]]
        map_view['zoom'] = 20

        species_df = update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/crack_species_only_Orthomosaic_downsample.tif',whole_geotiff_polygon(ard_bay_diver_url))
        species_bar = update_species_plots(species_df)

        species_time_series_counts = [update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/crack_species_only_Orthomosaic_downsample.tif',whole_geotiff_polygon(ard_bay_diver_url))['coverage_sqm'][0],
        update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/CRACK_ID_pink_downsample.tif',whole_geotiff_polygon(ard_bay_url))['coverage_sqm'][0]]
        species_time_series_years = [2022,2023]
        species_time_series_df = pd.DataFrame(list(zip(species_time_series_years, species_time_series_counts)),
               columns =['year', 'pixel_area_count'])
        species_time_series_plot = update_species_time_plots(species_time_series_df)
    
     
    if survey_name == 'Loch Creran Serpulids' or Creran_serp_clicks != intermediate_Creran_serp_clicks :
        map_view['center'] =  [Creran_serp_center_coords[1],Creran_serp_center_coords[0]]
        map_view['zoom'] = 20
        species_df = update_sepcies_df('/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/ortho_geotiff/CreranSerpClassified_downsample.tif',whole_geotiff_polygon(Creran_serp_ID_url))
        species_time_series_df = species_time_series_df_initial
        # Update plots
        species_bar = update_species_plots(species_df)
        species_time_series_plot= update_species_time_plots(species_time_series_df)

    if survey_name == 'Loch Creran NMPI T1' or Creran_15_03_23_T1_clicks != intermediate_Creran_15_03_23_T1_clicks:
        map_view['center'] =  [Creran_15_03_23_T1_center_coords[1],Creran_15_03_23_T1_center_coords[0]]
        map_view['zoom'] = 20
        # Update plots
        species_df = species_df_initial
        species_time_series_df = species_time_series_df_initial
        species_bar = update_species_plots(species_df)
        species_time_series_plot= update_species_time_plots(species_time_series_df)


    ## probaly terible logic to deal with events: drop down choice or clicks 
    else:
        if survey_name  not in survey_location_list[1:] or ard_bay_marker_clicks!= intermediate_ard_bay_click or Creran_15_03_23_T1_clicks != intermediate_Creran_15_03_23_T1_clicks or Creran_serp_clicks != intermediate_Creran_serp_clicks:  
             # Update plots
            if  'species_df' not in locals() :
                species_bar = update_species_plots(species_df_initial)
            if  'species_time_series_df' not in locals() : 
                species_time_series_plot= update_species_time_plots(species_time_series_df_initial)
        else:
            species_bar = update_species_plots(species_df)
            species_time_series_plot= update_species_time_plots(species_time_series_df)


    if ard_bay_marker_clicks:
        intermediate_ard_bay_click =  ard_bay_marker_clicks


    if Creran_15_03_23_T1_clicks:
        intermediate_Creran_15_03_23_T1_clicks =  Creran_15_03_23_T1_clicks


    if Creran_serp_clicks:
        intermediate_Creran_serp_clicks =  Creran_serp_clicks

    if map_view != intermediate_mapview:
        survey_name_out = 'none'
    else:
        survey_name_out=survey_name


    if not intermediate_mapview:
        intermediate_mapview = map_view


    if 'map_children_new' not in locals() :

        map_children = initial_map_children
    else:
        map_children = map_children_slide

    return  species_bar, species_time_series_plot,  intermediate_mapview, survey_name_out, map_view, info_out, intermediate_ard_bay_click, intermediate_Creran_15_03_23_T1_clicks,intermediate_Creran_serp_clicks, map_children




# @app.callback(Output("info",component_property='children'),
#               Input("intermediate_polygon", "data"),
#               Input("date_select_slide","value")
#               )


# def show_intermediate_variables(intermediate_polygon,slider_value):
#     print('cb3')
#     if intermediate_polygon is None:
#         raise PreventUpdate
#     print(type(intermediate_polygon))
    
#     return str(type(intermediate_polygon))+str(slider_value)


if __name__ == '__main__':
    app.run_server(debug=True,port=8053)
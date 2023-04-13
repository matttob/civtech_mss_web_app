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





external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


logo_image_path = 'assets/Logo2.png'



# # Using base64 encoding and decoding
# def b64_image(image_filename):
#     with open(image_filename, 'rb') as f:
#         image = f.read()
#     return 'data:image/png;base64,' + base64.b64encode(image).decode('utf-8')


# define functions external to app call backs


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
    entire_geotiff_poly = bounded_data
    return entire_geotiff_poly


# Enter tiler details
titiler_endpoint= "https://os8ci3nx02.execute-api.eu-west-2.amazonaws.com"  # titiler docker image running on local .


# survey locations
survey_location_list = ['none','Ardmucknish Bay','Loch Creran T1']



ard_bay_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_ROV_20_10_2_5mmPix_wgs84_test.tif"
ard_bay_request = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": ard_bay_url,
        "rescale": f"{0},{255}",
    }
).json()


ard_bay_center_coords  = get_centre_geotiff(ard_bay_url)
ard_bay_whole_geotiff_polygon = whole_geotiff_polygon(ard_bay_url)
ard_bay_marker = dl.Marker(id='test', position=(ard_bay_center_coords[1], ard_bay_center_coords[0]))

pink_t0_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_CRACK_ID_pink_downsample.tif"
request_pink_t0= httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": pink_t0_url,
        "rescale": f"{0},{255}",
    }
).json()

# Extract min and max values of the COG , this is used to rescale the COG
bathy_dem_url = "https://tiletesting.s3.eu-west-2.amazonaws.com/COG_CRACK_DEM.tif"
r = httpx.get(
    f"{titiler_endpoint}/cog/statistics",
    params = {
        "url": bathy_dem_url,
    }
).json()

minv = (r["b1"]["min"])
maxv = (r["b1"]["max"])


request_bathy_dem_url = httpx.get(
    f"{titiler_endpoint}/cog/tilejson.json",
    params = {
        "url": bathy_dem_url,
        "rescale": f"{minv},{maxv}",
        "colormap_name": "viridis"
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





date_slider_file_dict = {2021 : '/Users/matthewtoberman/Downloads/CRACK_ID_pink_downsample.tif', 
                            2022 : '/Users/matthewtoberman/Dropbox/TRITONIA/CIVTECH/PORTAL/data/crack_species_only_Orthomosaic_downsample.tif'}




species_df_initial = pd.DataFrame(['pink'],columns=['Species'])
species_df_initial['Pixel Count'] = 0
species_df_initial['coverage_sqm']= 0
species_df_initial.loc[len(species_df_initial)] = ['blue',0,0] 
species_df_initial.loc[len(species_df_initial)] = ['none',1,1] 


species_time_series_df_initial_counts = [0]
species_time_series_df_initial_years = [2021,2022]

species_time_series_df_initial = pd.DataFrame(list(zip(species_time_series_df_initial_years, species_time_series_df_initial_counts)),
               columns =['year', 'pixel_area_count'])

species_pie = px.pie(species_df_initial,values='Pixel Count', names='Species', color='Species',color_discrete_map={'pink':'DeepPink',
                                'blue':'Cyan',
                                'none':'DimGray'})

species_bar = px.bar(species_df_initial[species_df_initial['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
                     color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
                     labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (m\u00b2) '},
                     range_y=[0, 8])


species_bar.update_layout(
     showlegend=False,
    xaxis = dict(
        showgrid=False),
         yaxis=dict(showgrid=False))


species_time_series_plot = px.line(species_time_series_df_initial,x='year',y='pixel_area_count',
                                    range_x=[2020, 2022],
                                    range_y=[0, 8],
                                    labels={'year': 'Year','pixel_area_count': 'Area Covered  (m\u00b2) '})

species_time_series_plot.update_layout(
    xaxis = dict(
        tickmode = 'array',
        tickvals = [2020,2021,2022],
        ticktext = ['2020', '2021', '2022'],
        showgrid=False),
         yaxis=dict(showgrid=False))


# hack to find pixel area in future this shoudl be 
dataset = gdal.Open('/Users/matthewtoberman/Downloads/CRACK_ID_blue_flipped_downsample_metres.tif') 
got = dataset.GetGeoTransform()
pixel_area = abs(got[1]*got[5])



def get_style(feature):
    color = 'yellow'
    return dict(fillColor=color, weight=2, opacity=1, color='white', dashArray='3', fillOpacity=0.7)




# creat dash app

app = Dash(__name__)
start_zoom = 8
map_centre_coords = [56.5314423498172, -5.619001454153479]
# start_mapview={'center': [56.00000078923048, -5.0019120057804844], 'zoom': 16}

#create the info panel where text can be displayed
info = html.Div( id="info", className="info",
                style={"position": "absolute", "bottom": "10px", "left": "10px", "z-index": "1000"})

#Create app layout 
app.layout = html.Div([
     html.Div([
dcc.Graph(id='species_pie',
            figure=species_pie,style={'width': '300px', 'height': '300px','float': 'left','margin': 'auto'}),
dcc.Graph(id='species_bar',
            figure=species_bar,style={'width': '300px', 'height': '300px','float': 'left','margin': 'auto'}),
dcc.Graph(id='species_time_series_plot',
            figure=species_time_series_plot,style={'width': '300px', 'height': '300px','float': 'left','margin': 'auto'})]),
dl.Map(style={'width': '800px', 'height': '400px','margin': '30px'},
               center=map_centre_coords,
               zoom=start_zoom,
               maxZoom=1000,
               id = "map",
               children=[ 
            dl.LayersControl([
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_bathy_dem_url["tiles"][0],id="bathy", maxZoom=1000)),name="bathy",checked=True),
                   #COG fed into Tilelayer using TiTiler url (taken from r["tiles"][0])
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_request["tiles"][0],id="ortho")),name="Ortho",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_pink_t0["tiles"][0], opacity=0.4,id="species_pink")),name="Species_pink",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Crean_15_03_23_T1_ortho")),name="Crean_15_03_23_T1_Ortho",checked=True),
                   dl.LayerGroup(id="layer"),
                   info]),
                dl.FeatureGroup([dl.EditControl(id="edit_control")]),
                ]),
html.Div(children=[
                html.Label(['Select Survey:'], style={'font-weight': 'bold', "text-align": "center"}),
                dcc.Dropdown(id = 'survery_select',
                        options=survey_location_list,
                        value='none',  # initial value displayed when page first loads
                        clearable=False)],
                        style=dict(width='25%')),
html.Div([
dcc.RangeSlider(
id='date_select_slide',
min=2021,
max=2022,
value=[2021,2021],
step=1,
marks={
        2021: '2021',
        2022: '2022'
    },
),
], style= {'width': '500px','float': 'left','margin': '60px'}),
html.Img(src=logo_image_path,style={'height':'10%', 'width':'10%'}),     
dcc.Store(id='intermediate_polygon'),
dcc.Store(id='intermediate_slider'),
dcc.Store(id = 'species_area_time_series'),
dcc.Store(id = 'intermediate_mapview')
          
])



@app.callback(Output("species_pie",component_property='figure'),
              Output("species_bar",component_property='figure'),
              Output("map", "children"),
              Output('intermediate_polygon','data'),
              Output('intermediate_slider','data'),
              Output("species_time_series_plot",component_property='figure'),
              Output('intermediate_mapview','data'),
              Output("survery_select", component_property='value'),
              Output("map", "viewport"),
              Output("info",component_property='children'),
              Input("date_select_slide","value"),
              Input('intermediate_slider','data'),
              Input('intermediate_polygon','data'),
              Input("edit_control", "geojson"),
              Input("map", "viewport"),
              Input("survery_select", component_property='value'),
              Input('intermediate_mapview','data'),
              )

def count_species_cover_in_polygon(slider_values,intermediate_slider,intermediate_polygon,polygon_json,map_view,survey_name,intermediate_mapview):


    # update info box with file name used for slider values
    info_out = str(date_slider_file_dict[slider_values[0]].split('/')[-1])





   
    if map_view is None:
          map_view = {'center': [56.58215811323581, -5.701866236751068], 'zoom': 9}
    # if type(map_view) != 'NoneType' and type(intermediate_mapview ) != 'NoneType' :
    #         intermediate_mapview = start_mapview
    # #         current_zoom = map_view['zoom']
    #         print(f'intermediate = {intermediate_mapview}')



    if survey_name == 'Ardmucknish Bay':
        map_view['center'] =  [ard_bay_center_coords[1],ard_bay_center_coords[0]]
        map_view['zoom'] = 20



 


        if polygon_json is None:
            print('test_no_user_poly')
            entire_ortho_poly= Polygon([[whole_geotiff_polygon(ard_bay_url)['bounds'][0],whole_geotiff_polygon(ard_bay_url)['bounds'][1]],
                      [whole_geotiff_polygon(ard_bay_url)['bounds'][2],whole_geotiff_polygon(ard_bay_url)['bounds'][1]],
                      [whole_geotiff_polygon(ard_bay_url)['bounds'][2],whole_geotiff_polygon(ard_bay_url)['bounds'][3]],
                      [whole_geotiff_polygon(ard_bay_url)['bounds'][0],whole_geotiff_polygon(ard_bay_url)['bounds'][3]]])
                  
            with rasterio.open(date_slider_file_dict[slider_values[0]]) as src:
                pink_out_image, out_transform = rasterio.mask.mask(src,[entire_ortho_poly], crop=True,pad=True,nodata=99)

            pink_non_zero_alpha_band_count = ((pink_out_image[3,:,:] ==  255)).sum()
            print(pink_non_zero_alpha_band_count)
            # count no species coloured pixels
            no_species_count = ((pink_out_image[3,:,:] != 99)).sum()-((pink_out_image[3,:,:] ==  255)).sum()

            # create data frame for species plots
            species_df = pd.DataFrame(['pink'],columns=['Species'])
            species_df['Pixel Count'] = pink_non_zero_alpha_band_count
            species_df['coverage_sqm']= pink_non_zero_alpha_band_count*pixel_area
            species_df.loc[len(species_df)] = ['blue',0,0] 
            species_df.loc[len(species_df)] = ['none',no_species_count,0] 

            species_pie = px.pie(species_df,values='Pixel Count', names='Species', color='Species',color_discrete_map={'pink':'DeepPink',
                                        'blue':'Cyan',
                                        'none':'DimGray'})

            species_bar = px.bar(species_df[species_df['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
                                    color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
                                    labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (m\u00b2) '},
                                    range_y=[0, 8])
            species_bar.update_layout(
            showlegend=False,
            xaxis = dict(
             showgrid=False),
            yaxis=dict(showgrid=False))

            species_time_series_plot = px.line(species_time_series_df_initial,x='year',y='pixel_area_count',
                                        range_x=[2020, 2022],
                                        range_y=[0, 8],
                                        labels={'year': 'Year','pixel_area_count': 'Area Covered  (m\u00b2) '})

            species_time_series_plot.update_layout(
                    xaxis = dict(
                        tickmode = 'array',
                        tickvals = [2020,2021,2022],
                        ticktext = ['2020', '2021', '2022'],
                        showgrid=False),
                        yaxis=dict(showgrid=False))


              





    if survey_name == 'Loch Creran T1':
        map_view['center'] =  [Creran_15_03_23_T1_center_coords[1],Creran_15_03_23_T1_center_coords[0]]
        map_view['zoom'] = 20
    
    
    if map_view != intermediate_mapview:
          survey_name_out = 'none'
    else: 
          survey_name_out = survey_name
          
    intermediate_mapview = map_view

    #  update plots depending polygon selection
    if intermediate_polygon:
        if not polygon_json:
            polygon_json  = copy.deepcopy(intermediate_polygon)
    
    if polygon_json is not None:
        if len(polygon_json['features'])>0:
            # convert json coordinatees to format expected by rasterio
            polygon_json_raterio = copy.deepcopy(polygon_json)
            polygon_json_raterio['features'][-1]['geometry']['coordinates'][0] = [tuple(polygon_json_raterio) for polygon_json_raterio in polygon_json_raterio['features'][-1]['geometry']['coordinates'][0] ]


            # compute over range slider values
           
            pink_non_zero_alpha_band_counts_year = []
            slider_values_intervals = range(slider_values[0], slider_values[1]+1, 1)
            
            for slide_interval_value in slider_values_intervals:
                            # read raster values from within polygon had to give boundaries of mask value of 99 to avoid zero padding
        
                with rasterio.open(date_slider_file_dict[slide_interval_value]) as src:
                    pink_out_image, out_transform = rasterio.mask.mask(src,[polygon_json_raterio['features'][-1]['geometry']], crop=True,pad=True,nodata=99)



                # count pixels in extracted polygon
                pink_non_zero_alpha_band_count = ((pink_out_image[3,:,:] ==  255)).sum()*pixel_area
                pink_non_zero_alpha_band_counts_year.append(pink_non_zero_alpha_band_count)
                
            species_time_series_df = pd.DataFrame(list(zip(list(slider_values_intervals), pink_non_zero_alpha_band_counts_year)),
               columns =['year', 'pixel_area_count'])

        
            
            # read raster values from within polygon had to give boundaries of mask value of 99 to avoid zero padding
            if slider_values[0]  == 2021:
                with rasterio.open(date_slider_file_dict[2021]) as src:
                    pink_out_image, out_transform = rasterio.mask.mask(src,[polygon_json_raterio['features'][-1]['geometry']], crop=True,pad=True,nodata=99)

            if slider_values[0] == 2022:
                with rasterio.open(date_slider_file_dict[2022]) as src:
                    pink_out_image, out_transform = rasterio.mask.mask(src,[polygon_json_raterio['features'][-1]['geometry']], crop=True,pad=True,nodata=99)

            # count pixels in extracted polygon
            pink_non_zero_alpha_band_count = ((pink_out_image[3,:,:] ==  255)).sum()
            pink_non_zero_alpha_band_count_decimal =(((pink_out_image[3,:,:] ==  255)).sum()/((pink_out_image[3,:,:] != 99)).sum())
            pink_non_zero_alpha_band_count_percent_text = f"{pink_non_zero_alpha_band_count_decimal*100:.2f}%"
            

            
            # count no species coloured pixels
            no_species_count = ((pink_out_image[3,:,:] != 99)).sum()-((pink_out_image[3,:,:] ==  255)).sum()

            # create data frame for species plots
            species_df = pd.DataFrame(['pink'],columns=['Species'])
            species_df['Pixel Count'] = pink_non_zero_alpha_band_count
            species_df['coverage_sqm']= pink_non_zero_alpha_band_count*pixel_area
            species_df.loc[len(species_df)] = ['blue',0,0] 
            species_df.loc[len(species_df)] = ['none',no_species_count,0] 

            species_pie = px.pie(species_df,values='Pixel Count', names='Species', color='Species',color_discrete_map={'pink':'DeepPink',
                                        'blue':'Cyan',
                                        'none':'DimGray'})

            species_bar = px.bar(species_df[species_df['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
                                    color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
                                    labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (m\u00b2) '},
                                    range_y=[0, 8])
            species_bar.update_layout(
            showlegend=False,
            xaxis = dict(
             showgrid=False),
            yaxis=dict(showgrid=False))


            species_time_series_plot = px.line(species_time_series_df,x='year',y='pixel_area_count',
                                    range_x=[2020, 2022],
                                    range_y=[0, 8],
                                    labels={'year': 'Year','pixel_area_count': 'Area Covered  (m\u00b2) '})
            species_time_series_plot.update_layout(
                                        xaxis = dict(
                                        tickmode = 'array',
                                        tickvals = [2020,2021,2022],
                                 ticktext = ['2020', '2021', '2022']))
            species_time_series_plot.update_traces(line_color='DeepPink', line_width=2)
            species_time_series_plot.update_layout(
             xaxis = dict(
            tickmode = 'array',
            tickvals = [2020,2021,2022],
            ticktext = ['2020', '2021', '2022'],
            showgrid=False),
            yaxis=dict(showgrid=False))


        else:
            if survey_name != 'Ardmucknish Bay':
                print('overwrite_zero_test')
                species_df = pd.DataFrame(['pink'],columns=['Species'])
                species_df['Pixel Count'] = 0
                species_df['coverage_sqm']= 0
                species_df.loc[len(species_df)] = ['blue',0,0] 
                species_df.loc[len(species_df)] = ['none',1,1] 


                species_pie = px.pie(species_df,values='Pixel Count', names='Species', color='Species',color_discrete_map={'pink':'DeepPink',
                                                'blue':'Cyan',
                                                'none':'DimGray'})
                
                species_bar = px.bar(species_df[species_df['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
                                    color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
                                        labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (m\u00b2) '},
                                        range_y=[0, 5])
                
                species_time_series_plot = px.line(species_time_series_df_initial,x='year',y='pixel_area_count',
                                        range_x=[2020, 2022],
                                        range_y=[0, 8],
                                        labels={'year': 'Year','pixel_area_count': 'Area Covered  (m\u00b2) '})

                species_time_series_plot.update_layout(
                    xaxis = dict(
                        tickmode = 'array',
                        tickvals = [2020,2021,2022],
                        ticktext = ['2020', '2021', '2022'],
                        showgrid=False),
                        yaxis=dict(showgrid=False))


                edit_control_sqm_area = 0
                pink_non_zero_alpha_band_count = 0   

    # else:
    #     species_df = pd.DataFrame(['pink'],columns=['Species'])
    #     species_df['Pixel Count'] = 0
    #     species_df['coverage_sqm']= 0
    #     species_df.loc[len(species_df)] = ['blue',0,0] 
    #     species_df.loc[len(species_df)] = ['none',1,1] 


    #     species_pie = px.pie(species_df,values='Pixel Count', names='Species', color='Species',color_discrete_map={'pink':'DeepPink',
    #                                     'blue':'Cyan',
    #                                     'none':'DimGray'})
        
    #     species_bar = px.bar(species_df[species_df['Species']!= 'none'],x='Species',y='coverage_sqm', color='Species',
    #                         color_discrete_map={'pink':'DeepPink','blue':'Cyan'},
    #                             labels={'Species': 'Species Type','coverage_sqm': 'Area Covered  (m\u00b2) '},
    #                             range_y=[0, 5])
        
    #     species_time_series_plot = px.line(species_time_series_df_initial,x='year',y='pixel_area_count',
    #                             range_x=[2020, 2022],
    #                             range_y=[0, 8],
    #                             labels={'year': 'Year','pixel_area_count': 'Area Covered  (m\u00b2) '})

    #     species_time_series_plot.update_layout(
    #         xaxis = dict(
    #             tickmode = 'array',
    #             tickvals = [2020,2021,2022],
    #             ticktext = ['2020', '2021', '2022'],
    #             showgrid=False),
    #             yaxis=dict(showgrid=False))


    #     edit_control_sqm_area = 0
    #     pink_non_zero_alpha_band_count = 0



    intermediate_slider_value_dict = {'value': slider_values[0]}


    # update map based on slider positio
                
    # if not map_view:
    #     current_zoom = start_zoom
    # else:
    #     current_zoom = map_view['zoom']

  
    if slider_values[0] == 2021 and  map_view['zoom'] <= 20:
                map_children=[ 
            dl.LayersControl([
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                   #COG fed into Tilelayer using TiTiler url (taken from r["tiles"][0])
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_bathy_dem_url["tiles"][0],id="bathy", maxZoom=1000)),name="bathy",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_request["tiles"][0],id="ortho")),name="Ortho",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_pink_t0["tiles"][0], opacity=0.4,id="species_pink")),name="Species_pink",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Crean_15_03_23_T1_ortho")),name="Crean_15_03_23_T1_Ortho",checked=True),
                   dl.LayerGroup(id="layer"),
                   info]),
            dl.FeatureGroup([dl.EditControl(id="edit_control")]),
            ard_bay_marker,
            Creran_15_03_23_T1_marker]
    
    if slider_values[0]  == 2022 and  map_view['zoom'] <= 20:
                map_children=[ 
            dl.LayersControl([
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                                      dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_bathy_dem_url["tiles"][0],id="bathy", maxZoom=1000)),name="bathy",checked=True),

                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_diver_request["tiles"][0],id="ortho")),name="Ortho",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_diver_request_pink_t0["tiles"][0], opacity=0.4,id="species_pink")),name="Species_pink",checked=True),
                     dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Crean_15_03_23_T1_ortho")),name="Crean_15_03_23_T1_Ortho",checked=True),
                   dl.LayerGroup(id="layer"),
                   info]),
            dl.FeatureGroup([dl.EditControl(id="edit_control")]),
            ard_bay_marker,
            Creran_15_03_23_T1_marker]



    if slider_values[0] == 2021 and  map_view['zoom'] > 20:
                map_children=[ 
            dl.LayersControl([
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_bathy_dem_url["tiles"][0],id="bathy", maxZoom=1000)),name="bathy",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_request["tiles"][0],id="ortho")),name="Ortho",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_pink_t0["tiles"][0], opacity=0.4,id="species_pink")),name="Species_pink",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Crean_15_03_23_T1_ortho")),name="Crean_15_03_23_T1_Ortho",checked=True),
                   dl.LayerGroup(id="layer"),
                   info]),
                   dl.FeatureGroup([dl.EditControl(id="edit_control")]),
]
    
    if slider_values[0]  == 2022 and  map_view['zoom'] > 20:
                map_children=[ 
            dl.LayersControl([
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",id="TileMap")),name="BaseMap",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=request_bathy_dem_url["tiles"][0],id="bathy", maxZoom=1000)),name="bathy",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_diver_request["tiles"][0],id="ortho")),name="Ortho",checked=True),
                   dl.Overlay(dl.LayerGroup(dl.TileLayer(url=ard_bay_diver_request_pink_t0["tiles"][0], opacity=0.4,id="species_pink")),name="Species_pink",checked=True),
                     dl.Overlay(dl.LayerGroup(dl.TileLayer(url=Creran_15_03_23_T1_request["tiles"][0],id="Crean_15_03_23_T1_ortho")),name="Crean_15_03_23_T1_Ortho",checked=True),
                   dl.LayerGroup(id="layer"),
                   info]),
                     dl.FeatureGroup([dl.EditControl(id="edit_control")]),
]
                    
    


    return species_pie , species_bar , map_children, polygon_json , intermediate_slider, species_time_series_plot, intermediate_mapview, survey_name_out, map_view, info_out





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
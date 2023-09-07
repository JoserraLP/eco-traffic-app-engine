import os
import webbrowser

import gmplot
import pandas as pd

from eco_traffic_app_engine.engine.eco_traffic_engine import EcoTrafficEngine
from eco_traffic_app_engine.graph.models import Coords
from eco_traffic_app_engine.others.utils import remove_files
from eco_traffic_app_engine.routing.graphhopper import GraphHopper
from eco_traffic_app_engine.routing.ors import OpenRouteService
from eco_traffic_app_engine.routing.osrm import OSRM
from eco_traffic_app_engine.static.constants import CONGESTION_DATA_DIR


def plot_points_on_map(coordinates: list):
    """
    Plot and show all the coordinates on an HTML map

    :param coordinates: list of coordinates (lon, lat)
    :type coordinates: list
    :return:
    """
    # Coordinates are reversed
    df = pd.DataFrame(coordinates, columns=['lon', 'lat'])

    # Parse lat and lon columns to numeric
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    # Create a map plot with center the mean of the latitude and longitude with a zoom of 10
    gmap = gmplot.GoogleMapPlotter(df['lat'].mean(), df['lon'].mean(), zoom=10)
    # Insert the information into the plot
    gmap.scatter(df['lat'], df['lon'], color='red', size=40, marker=False)
    # Define file where map will be stored
    map_file = 'map.html'
    # Draw on the selected file
    gmap.draw(map_file)
    # Open the file in the browser
    webbrowser.open(map_file)


if __name__ == "__main__":

    # Test coords
    """
    # Caceres
    coords = [Coords(lat=39.47251341839538, lon=-6.392090320587159), 
              Coords(lat=39.464897947423665, lon=-6.367006301879884)]

    # Caceres
    coords = [Coords(lat=39.4683671, lon=-6.3888294), Coords(lat=39.4683589, lon=-6.3834670), 
              Coords(lat=39.4633199, lon=-6.3794062), Coords(lat=39.4610183, lon=-6.3795993),
              Coords(lat=39.4634970, lon=-6.3630152), Coords(lat=39.4783447, lon=-6.3539399), 
              Coords(lat=39.4823134, lon=-6.3611832), Coords(lat=39.47484578780288, lon=-6.3808747113865145), 
              Coords(lat=39.4722619, lon=-6.3816901), Coords(lat=39.47138379498617, lon=-6.3822765054919355), 
              Coords(lat=39.4720186, lon=-6.3879262), Coords(lat=39.4683671, lon=-6.3888294)]
              
    # Caceres
    coords = [Coords(lat=39.466836904555095, lon=-6.380049232359181), 
              Coords(lat=39.46838573016692, lon=-6.383509281974666), 
              Coords(lat=39.46976059462188, lon=-6.383715812065494)]

    # Caceres
    coords = [Coords(lat=39.466836904555095, lon=-6.380049232359181),
              Coords(lat=39.46976059462188, lon=-6.383715812065494)]

    # From Badajoz to Cáceres
    coords = [Coords(lat=38.878484746466725, lon=-6.9594161644033425), 
              Coords(lat=39.47913097271268, lon=-6.342439773471694)]

    # Gijon - Caceres
    coords = [Coords(lat=43.52311256, lon=-5.62778751), 
              Coords(lat=39.47012875669537, lon=-6.385007480006402)]

    """

    # Gijon coords
    coords = [Coords(lat=43.5231781, lon=-5.6276553),
              Coords(lat=43.3828673, lon=-5.8237067)]

    # OpenRouteService -> 92 nodes
    # GraphHopper -> 81 nodes
    # OSRM -> 62 nodes

    """ OSRM query """

    query_params = {
        "alternatives": 0,
        "geometries": "geojson",
        "annotations": "nodes"
    }

    osrm = OSRM(params=query_params)

    routes = osrm.get_routes(coords)

    """ GraphHopper query """
    """
    query_params = {
        "profile": "car",
        "point": [f"{coord.lat},{coord.lon}" for coord in coords], # point has more than one value
        "locale": "en",
        "elevation": "false",
        "optimize": "false",
        "instructions": "true",
        "calc_points": "true",
        "debug": "false",
        "points_encoded": "false",
        "ch.disable": "true",
        "heading": "0",
        "heading_penalty": "120",
        "pass_through": "false",
        "round_trip.distance": "10000",
        "round_trip.seed": "0",
        "key": os.environ.get("GRAPHHOPPER_KEY")
    }
    graphhopper = GraphHopper(params=query_params)

    routes = graphhopper.get_routes()
    """
    """ OpenRouteService query """
    """
    # query_params = {"share_factor": 0.6, "target_count": 1, "weight_factor": 0.8}
    query_params = {}
    osr = OpenRouteService(params=query_params)

    routes = osr.get_routes(coords)
    """
    # Plot points on map
    coordinates = [(coords.lon, coords.lat) for coords in routes[0]['segments']]
    plot_points_on_map(coordinates)

    # Start Eco-Traffic Engine with the given routes
    engine = EcoTrafficEngine(routes)

    # Process the routes
    engine.process_routes()

    # Request, process and store congestion data
    # engine.process_congestion_data()

    # Once data is processed, remove congestion data
    # remove_files(CONGESTION_DATA_DIR)

    # Extend missing information on graph (maximum speed, number of lanes, ...)
    # engine.extend_graph_info()

import os

from eco_traffic_app_engine.engine.eco_traffic_engine import EcoTrafficEngine
from eco_traffic_app_engine.others.utils import remove_files
from eco_traffic_app_engine.routing.graphhopper import GraphHopper
from eco_traffic_app_engine.routing.osrm import OSRM
from eco_traffic_app_engine.static.constants import CONGESTION_DATA_DIR

if __name__ == "__main__":
    # Test coords
    coords = [[39.47251341839538, -6.392090320587159], [39.464897947423665, -6.367006301879884]]

    coords = [[39.4683671, -6.3888294], [39.4683589, -6.3834670], [39.4633199, -6.3794062], [39.4610183, -6.3795993],
              [39.4634970, -6.3630152], [39.4783447, -6.3539399], [39.4823134, -6.3611832],
              [39.47484578780288, -6.3808747113865145], [39.4722619, -6.3816901],
              [39.47138379498617, -6.3822765054919355], [39.4720186, -6.3879262], [39.4683671, -6.3888294]]

    # From Badajoz to Cáceres
    # coords = [[38.878484746466725, -6.9594161644033425], [39.47913097271268, -6.342439773471694]]

    """ OSRM query """
    """
    query_params = {
        "alternatives": 0,
        "geometries": "geojson",
        "annotations": "nodes"
    }

    osrm = OSRM(params=query_params)

    routes = osrm.get_routes(coords)
    """

    """ GraphHopper query """
    query_params = {
        "profile": "car",
        "point": [f"{coord[0]},{coord[1]}" for coord in coords], # point has more than one value
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

    # Query in Neo4j -> Maybe the distance is not the same as the one in the route
    # MATCH ()-[r]->() RETURN sum(r.distance)

    # Start Eco-Traffic Engine with the given routes
    engine = EcoTrafficEngine(routes)

    # Process the routes
    engine.process_routes()

    # Request, process and store congestion data
    engine.process_congestion_data()

    # Once data is processed, remove congestion data
    remove_files(CONGESTION_DATA_DIR)

    # Extend missing information on graph (maximum speed, number of lanes, ...)
    engine.extend_graph_info()

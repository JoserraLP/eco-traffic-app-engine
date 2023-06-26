
from eco_traffic_app_engine.engine.eco_traffic_engine import EcoTrafficEngine
from eco_traffic_app_engine.others.utils import remove_files
from eco_traffic_app_engine.routing.osrm import OSRM
from eco_traffic_app_engine.static.constants import CONGESTION_DATA_DIR

if __name__ == "__main__":
    # Test coords
    coords = [[39.47251341839538, -6.392090320587159], [39.464897947423665, -6.367006301879884]]

    # From Badajoz to Cáceres
    # coords = [[38.878484746466725, -6.9594161644033425], [39.47913097271268, -6.342439773471694]]

    query_params = {
        "alternatives": 0,
        "geometries": "geojson",
        "annotations": "nodes"
    }

    # Query in Neo4j -> Maybe the distance is not the same as the one in the route
    # MATCH ()-[r]->() RETURN sum(r.distance)

    osrm = OSRM(params=query_params)

    routes = osrm.get_routes(coords)

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

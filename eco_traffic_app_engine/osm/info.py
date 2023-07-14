import requests
from OSMPythonTools.api import Api
from OSMPythonTools.overpass import Overpass

from eco_traffic_app_engine.graph.models import Node
from eco_traffic_app_engine.static.constants import HEIGHT_API_URL


class OSMRetriever:
    """
    Class for storing Overpass, OSM API instance and other utils
    """

    def __init__(self):
        self._overpass = Overpass()
        self._api = Api()

    def get_osm_node_info(self, node_id: str) -> Node:
        """
        Retrieve the OSM node information based on the node ID

        :param node_id: node identifier
        :type node_id: str
        :return: node instance with the requested data
        :rtype: Node
        """
        # Get info from OSM
        node_result = self._api.query('node/' + str(node_id))

        # Get info from "Height" service
        height_result = requests.get(url=HEIGHT_API_URL + f"{node_result.lat()},{node_result.lon()}").json()

        # Store value retrieved or -1 as invalid value
        height = height_result['results'][0]['elevation'] if len(height_result['results']) > 0 else -1

        return Node(name=node_id, lat=node_result.lat(), lon=node_result.lon(), height=height)

    def remove_non_intersections_nodes(self, nodes: list) -> list:
        """
        Remove all those OSM nodes that are not intersections

        :param nodes: OSM nodes identifiers
        :type nodes: list
        :return: updated list removing OSM non-intersection nodes
        :rtype: list
        """

        return [node for node in nodes if
                int(self._overpass.query(f'node(id:{node});way(bn)["highway"];out count;')._json['elements'][0]
                    ['tags']['ways']) > 1]

    def remove_empty_nodes(self, nodes: list, traffic_lights: bool = False) -> list:
        """
        Remove all those OSM nodes with no information ('highway' tag does not exist)

        :param nodes: OSM nodes identifiers
        :type nodes: list
        :param traffic_lights: flag to retrieve only traffic lights. Default to False.
        :type traffic_lights: bool
        :return: updated list removing empty OSM nodes
        :rtype: list
        """
        # Define coordinates str based on coordinates (lat, lon)
        nodes_union_str = '\n'.join([f"node(id:{node});" for node in nodes])
        # Create traffic light query filter
        traffic_light_str = '=traffic_signals' if traffic_lights else ''

        # Query to get the nodes by its around areas and use union for retrieving all the nodes for a given segment
        query = f'({nodes_union_str}) ->.all_nodes; node.all_nodes[highway{traffic_light_str}]; out;'

        # Execute query
        results = self._overpass.query(query)
        return [item._json['id'] for item in results.elements()]

    def get_osm_nodes(self, road_coords: list) -> list:
        """
        Get those osm nodes that are related to a given pair of coordinates

        :param road_coords: coordinates pair list
        :type road_coords: list
        :return: list with nodes related to the coordinates
        :rtype: list
        """
        # Define coordinates str based on coordinates (lat, lon)
        osm_nodes = []

        # It can not be done as a grouped query as the results are ordered by ID and the graph is not created well

        for coords in road_coords:
            # Query to get the nodes by its around areas
            query = f'node(around:1,{coords[1]},{coords[0]}); out;'

            # Execute query
            results = self._overpass.query(query)

            osm_nodes += [item._json['id'] for item in results.elements()]

        return osm_nodes

    def get_osm_way_info(self, node_id: str) -> list:
        """
        Get the information related to an OSM way based on a given node

        :param node_id: node identifier
        :type node_id: str
        :return: list with the ways of a given node
        :rtype: list
        """
        # Get osm way by node id
        query = f"node(id:{node_id});way(bn);out;"

        # Execute query
        results = self._overpass.query(query)

        return [item._json for item in results.elements()]

    def is_in_roundabout(self, node_id: str) -> bool:
        """
        Check if the node is in a roundabout
        :param node_id: node identifier
        :type node_id: str
        :return: True if the node is in a roundabout, otherwise False
        :rtype: bool
        """
        # Get the ways with junction type = roundabout
        query = f"node(id:{node_id});way(bn)[junction=roundabout];out;"

        # Execute query
        results = self._overpass.query(query)

        return len(results.elements()) >= 1

    def filter_around(self, center: str, nodes: list, distance: float) -> list:
        """
        Get those nodes that are within a given distance from the center

        :param center: center node
        :type center: str
        :param nodes: nodes list
        :type nodes: list
        :param distance: radius distance
        :type distance: float
        :return: nodes that are within the radius
        :rtype: list
        """

        # Get query based on center variable and around distance
        query = f'(node(id:{center})->.center;\n' + 'node(id:' + ','.join([str(item) for item in nodes]) \
                + f')(around.center:{distance}););out;'

        # Execute query
        results = self._overpass.query(query)

        # Retrieve only the id
        return [item._json['id'] for item in results.elements()]

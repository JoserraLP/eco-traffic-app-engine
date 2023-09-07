import requests
from OSMPythonTools.api import Api
from OSMPythonTools.overpass import Overpass

from eco_traffic_app_engine.graph.models import Node, Coords
from eco_traffic_app_engine.static.constants import HEIGHT_API_URL


class OSMRetriever:
    """
    Class for storing Overpass, OSM API instance and other utils
    """

    def __init__(self):
        self._overpass = Overpass()
        self._api = Api()

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

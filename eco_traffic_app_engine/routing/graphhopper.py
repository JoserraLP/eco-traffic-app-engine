import requests
from eco_traffic_app_engine.osm.info import OSMRetriever


class GraphHopper:
    """
    GraphHopper service requestor
    """

    def __init__(self, params: dict):
        self._routes = []
        self._params = params

    def get_routes(self) -> list:
        """
        Get routes from GraphHopper service with the given params

        :return: routes
        :rtype: list
        """
        # Perform query
        response = requests.get("https://graphhopper.com/api/1/route",
                                params=self._params)

        osm_retriever = OSMRetriever()

        # Check if there exists the response
        if response.status_code == 200:
            # Store the routes from response
            routes = response.json()['paths']

            self._routes = [{'distance': route['distance'],
                             'duration': route['time']/1000.0,
                             'nodes': osm_retriever.get_osm_nodes(route['points']['coordinates'])}
                            for route in routes]

        return self._routes

    @property
    def routes(self):
        """
        Getter of routes

        :return: routes
        """
        return self._routes

    @routes.setter
    def routes(self, routes: list):
        """
        Setter of routes

        :param routes: routes
        :return:
        """
        self._routes = routes

    @property
    def params(self):
        """
        Getter of params

        :return: params
        """
        return self._params

    @params.setter
    def params(self, params: dict):
        """
        Setter of params

        :param params: params
        :return:
        """
        self._params = params

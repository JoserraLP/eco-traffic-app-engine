import requests


class OSRM:
    """
    Open Source Routing Machine service requestor
    """

    def __init__(self, params: dict):
        self._routes = []
        self._params = params

    def get_routes(self, coords: list) -> list:
        """
        Get routes from OSRM service with the given coords

        :param coords: list of pair coordinates
        :type coords: list
        :return: routes
        :rtype: list
        """
        # Perform query
        response = requests.get("https://router.project-osrm.org/route/v1/driving/" +
                                ";".join(f"{coord[1]},{coord[0]}" for coord in coords),
                                params=self._params)

        # Check if there exists the response
        if response:
            # Store the routes from response
            self._routes = response.json()['routes']

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

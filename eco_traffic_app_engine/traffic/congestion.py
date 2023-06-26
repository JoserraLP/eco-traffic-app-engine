import os

import pandas as pd
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass

from eco_traffic_app_engine.others.utils import concat, load_dataframe
from eco_traffic_app_engine.static.constants import CONGESTION_DATA_DIR, R_SCRIPT_DIRECTORY

import rpy2.robjects as ro


def request_congestion_data(congestion_center_nodes_str: str):
    """
    Perform the R script that requests the congestion information

    :param congestion_center_nodes_str: nodes used to request congestion data
    :type congestion_center_nodes_str: str
    :return: None
    """

    # Get MapBoxAPI Key from os.environment
    mapbox_api_key = os.environ.get("MAPBOX_API_KEY")
    if mapbox_api_key:
        # Set global variable as coordinates -> It will be accessed like this in R
        ro.globalenv['coordinates'] = congestion_center_nodes_str
        ro.globalenv['mapbox_key'] = mapbox_api_key
        r = ro.r
        # Use the R 'source' function to execute the R script
        r.source(R_SCRIPT_DIRECTORY)
    else:
        print("Error, MAPBOX_API_KEY environment variable not defined")
        exit(-1)


class TrafficCongestionRetriever:
    """
    Traffic Congestion Service Retriever
    """

    def __init__(self):
        self._congestion_data = None
        self._nominatim = Nominatim()
        self._overpass = Overpass()

    def process_congestion_data(self):
        """
        Perform all the processing of the congestion data

        :return:
        """

        # Load congestion dataset from directory
        congestion_df = load_dataframe(CONGESTION_DATA_DIR)

        # Check if data is loaded
        if not congestion_df.empty:
            # Process the congestion data
            self._congestion_data = self.process_congestion_geometries(congestion_df)

            # Parse 'osm_nodes' column of lists to a column of tuples to remove duplicate values
            self._congestion_data['osm_nodes'] = self._congestion_data['osm_nodes'].apply(tuple)

            # Remove duplicated elements
            self._congestion_data = self._congestion_data.drop_duplicates()

            # Group by class and congestion, concatenating the osm nodes for those roads with same value
            self._congestion_data = self._congestion_data.groupby(['class', 'congestion']).agg({'osm_nodes': concat})\
                .reset_index()

            # "Explode" the list of osm nodes into different rows
            self._congestion_data = self._congestion_data.explode('osm_nodes')

    def process_route_nodes_with_congestion(self, nodes: list):
        """
        Process and store only those nodes from the route that have congestion information

        :param nodes: graph route nodes
        :type nodes: list
        :return: None
        """
        # Get those nodes that are in the graph
        self._congestion_data = self._congestion_data[self._congestion_data['osm_nodes'].isin(nodes)]

        # Remove duplicated elements
        self._congestion_data = self._congestion_data.drop_duplicates()

    def get_osm_nodes(self, road_coords: list) -> list:
        """
        Get the OSM nodes related to a list of pair of coordinates

        :param road_coords: roads pair coordinates list
        :type road_coords: list
        :return: list with all the OSM nodes
        :rtype: list
        """
        # Define coordinates str based on coordinates (lat, lon)
        nodes_union_str = '\n'.join([f"node(around:1,{item[1]},{item[0]});" for item in road_coords])

        # Query to get the nodes by its around areas
        # Use union for retrieving all the nodes for a given segment
        # It is not required to define the output format
        query = f'({nodes_union_str}); out;'

        # Execute query
        results = self._overpass.query(query)

        return [item._json['id'] for item in results.elements()]

    def process_congestion_geometries(self, congestion_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process all the congestion geometries, storing the congestion per nodes

        :param congestion_df: congestion dataframe
        :type congestion_df: pd.DataFrame
        :return: DataFrame with road congestion information processed
        :rtype: pd.DataFrame
        """
        # Remove white and \n characters from the geometry column to obtain plain info
        congestion_df['geometry'] = congestion_df['geometry'].map(lambda x: x.strip().replace('\n', ''))

        # Create a list for storing information related to the roads info
        roads_info = []

        # Iterate over the congestion dataframe
        for idx, row in congestion_df.iterrows():

            # Remove 'list(' character and parse each 'c(' to a list
            geometry_coords = row['geometry'].replace('list(', '').replace('), ', '').replace(')', '').replace(' ', '') \
                .split('c(')

            # Remove empty values from the list
            geometry_coords.remove('')

            # Iterate over the geometry coordinates
            for coordinates in geometry_coords:
                # Initialize a list to store all the coordinates for a given list of coordinates
                processed_coordinates_list = []
                # Get the geometry coordinates as a list instead of a list
                # This is because the information is stored a coordinates values split by ,
                coordinates = coordinates.split(',')

                # Calculate the half size of the coordinates list to process the values
                half_size = int(len(coordinates) / 2)
                # Iterate over the coordinates list but only until the half as it's the representation of the
                # coordinates.
                for i in range(half_size):
                    # Append both index and list half size + index representing lat and lon
                    processed_coordinates_list.append((coordinates[i], coordinates[i + half_size]))

                # Get OSM nodes from the processed coordinates
                osm_nodes = self.get_osm_nodes(processed_coordinates_list)

                # Store road related information such as class, congestion and osm nodes
                roads_info.append({'class': row['class'], 'congestion': row['congestion'], 'osm_nodes': osm_nodes})

        # Return the dataframe related to the road information
        return pd.DataFrame(roads_info)

    @property
    def congestion_data(self):
        """
        Getter of congestion data

        :return: congestion data
        """
        return self._congestion_data

    @congestion_data.setter
    def congestion_data(self, congestion_data: pd.DataFrame):
        """
        Setter of congestion data

        :param congestion_data: congestion_data
        :return:
        """
        self._congestion_data = congestion_data

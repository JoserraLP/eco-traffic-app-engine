from dataclasses import asdict

import networkx as nx
import pandas as pd
from geopy.distance import geodesic as gd

from eco_traffic_app_engine.graph.db.neo4j import GraphDB
from eco_traffic_app_engine.graph.models import Node, Segment, Coords
from eco_traffic_app_engine.osm.info import OSMRetriever
from eco_traffic_app_engine.static.constants import *
from eco_traffic_app_engine.static.constants import CONGESTION_DICT
from eco_traffic_app_engine.traffic.congestion import *


class EcoTrafficEngine:
    """
    Engine of the EcoTraffic APP
    """

    def __init__(self, routes: list):
        # Initialize graph db and memory graph as directed graph
        self._graph_db = GraphDB(ip_address=GRAPH_DB_URL, user=GRAPH_DB_USER, password=GRAPH_DB_PASSWORD)
        self._graph = nx.DiGraph()

        # Initialize OSMRetriever
        self._osm_retriever = OSMRetriever()

        # Initialize traffic congestion class
        self._traffic_congestion_retriever = TrafficCongestionRetriever()

        # Initialize routes
        self._routes = routes

        # Create a dict with the coordinates and a related identifier
        self._coordinates_ids = {}

        # Last identifier used
        self._last_id = 0

        # Clean up the network database
        self._graph_db.clear_database()

    def get_coordinates_id(self, coords: Coords) -> str:
        """
        Get coordinates id for the graph based on its latitude and longitude
        :param coords:
        :return:
        """
        coords_str = f'{coords.lat};{coords.lon}'  # ID = lat;lon

        # Retrieve the node id if exists, otherwise calculate it and store it
        if coords_str in self._coordinates_ids:
            coords_id = self._coordinates_ids[coords_str]
        else:
            self._coordinates_ids[coords_str] = coords_id = self._last_id
            self._last_id += 1

        return str(coords_id)

    def create_node(self, node_info: Node, graph_db: bool = True) -> None:
        """
        Create a node in the memory graph and/or graph database

        :param node_info: Node information
        :type node_info: Node
        :param graph_db: flag for storing the node into the graph database. Default True.
        :type graph_db: bool
        :return: None
        """
        # Check if node exists
        if node_info.node_id not in self._graph.nodes:
            # Add node
            self._graph.add_node(node_info.node_id, lat=node_info.lat, lon=node_info.lon, height=node_info.height)

            # Check if it is required to store in the graph database
            if graph_db:
                self._graph_db.create_node(asdict(node_info))

    def create_relation(self, source_id: str, destination_id: str, segment_info: Segment, graph_db: bool = True) -> None:
        """
        Create a relation between source and destination nodes in the memory graph and/or graph database

        :param source_id: source node identifier
        :type source_id: str
        :param destination_id: destination node identifier
        :type destination_id: Node
        :param segment_info: segment information
        :type segment_info: Segment
        :param graph_db: flag for storing the relation into the graph database. Default True.
        :type graph_db: bool
        :return: None
        """
        # Store relation
        self._graph.add_edge(source_id, destination_id, slope=segment_info.slope, distance=segment_info.distance,
                             congestion=segment_info.congestion, max_speed=segment_info.max_speed, lanes=segment_info.lanes,
                             highway=segment_info.highway, name=segment_info.name, surface=segment_info.surface,
                             way_id=segment_info.way_id)
        # Check if it is required to store in the graph database
        if graph_db:
            self._graph_db.create_update_relation({'from': source_id, 'to': destination_id},
                                                  segment_info=asdict(segment_info))

    def process_routes(self):
        """
        Process all the routes and store them into the graphs

        :return:
        """
        for route in self._routes:

            # Retrieve segments
            segments = route['segments']

            # Iterate over pairs of coordinates creating only destination nodes
            for idx, (source, destination) in enumerate(zip(segments, segments[1:])):
                # Get only destination id
                source_id = self.get_coordinates_id(source)
                destination_id = self.get_coordinates_id(destination)

                # Create the destination node info
                source_node = Node(node_id=source_id, lat=source.lat, lon=source.lon, height=route['heights'][idx])
                destination_node = Node(node_id=destination_id, lat=destination.lat, lon=destination.lon,
                                        height=route['heights'][idx+1])

                # Store the source and destination nodes
                self.create_node(node_info=source_node)
                self.create_node(node_info=destination_node)

                # Create the segment info
                segment_info = Segment(slope=route['slopes'][idx], distance=route['distances'][idx],
                                       max_speed=route['max_speed'][idx], congestion=None, lanes=0, highway="",
                                       name="", surface="", way_id="")
                # Store the relation between them
                self.create_relation(source_id, destination_id, segment_info)

    def insert_congestion_graph(self, congestion_df: pd.DataFrame):
        """
        Insert congestion info into the graph

        :param congestion_df: nodes congestion information
        :type congestion_df: pd.DataFrame
        :return: None
        """
        # Iterate over the nodes congestion info
        for index, row in congestion_df.iterrows():
            # Get node id and congestion value
            node_id = row['osm_nodes']
            congestion = CONGESTION_DICT[row['congestion']]

            # Get neighbors of the node
            neighbors = list(self._graph.neighbors(node_id))
            # Iterate over the neighbors
            for neighbor in neighbors:
                # Add congestion to segment relation between source and destination
                self._graph[node_id][neighbor]['congestion'] = congestion
                # In the graph db, update only the info related to the congestion
                self._graph_db.create_update_relation({'from': node_id, 'to': neighbor}, {'congestion': congestion})

    def get_congestion_area_center_nodes(self) -> list:
        """
        Obtain those nodes that are at a given distance between them, to retrieve congestion info from "center" nodes

        :return: list with the nodes' information
        :rtype: list
        """
        all_nodes = prev_nodes = list(self._graph.nodes)

        # Center nodes
        congestion_nodes = []

        # Filter those nodes that are relevant (based on area)
        for node in all_nodes:

            # Get those nodes that are not in the area
            all_nodes = [item for item in all_nodes if item not in
                         self._osm_retriever.filter_around(node, all_nodes, CONGESTION_DISTANCE)]
            # Store the center node
            if prev_nodes != all_nodes:
                congestion_nodes.append(node)

            # Update the prev_nodes values
            prev_nodes = all_nodes

        return congestion_nodes

    def process_congestion_data(self) -> None:
        """
        Request, process and store congestion data

        :return: None
        """
        # Get those nodes that will be used to retrieve congestion area data
        congestion_center_nodes = self.get_congestion_area_center_nodes()

        # Get from nodes the latitude and longitude of each node represented as str split by comma
        congestion_center_nodes_str = ';'.join(f'{self._graph.nodes[i]["lat"]},{self._graph.nodes[i]["lon"]}'
                                               for i in congestion_center_nodes)

        # Request congestion data
        # request_congestion_data(congestion_center_nodes_str)

        # Process congestion data
        self._traffic_congestion_retriever.process_congestion_data()

        # Check those node that are in the routes
        self._traffic_congestion_retriever.process_route_nodes_with_congestion(self._graph.nodes)

        # Insert data into graph
        self.insert_congestion_graph(self._traffic_congestion_retriever.congestion_data)

    def extend_graph_info(self, graph_db: bool = True):
        """
        Extend graph information related to ways such as congestion, maxspeed, lanes, type of highway, name or surface
        if not set previously.

        :param graph_db: flag for storing the relation into the graph database. Default True.
        :type graph_db: bool
        :return:
        """
        # Define previous node info
        previous_relation = {}

        # First check if first node have information, otherwise search for it on its successors
        self.extend_initial_empty_nodes(graph_db)

        # Iterate over the graph by source-destination pair
        for u, v in self._graph.edges:
            # Extend relation info
            relation = self.extend_relation_info(u, v, previous_relation)

            # Extend the congestion and store the relation
            previous_relation = self.extend_congestion_data(u, v, relation)

            # Update relation data
            self._graph.add_edge(u, v, **relation)

            if graph_db:
                # Update database information
                self._graph_db.create_update_relation(relation={'from': u, 'to': v}, segment_info=relation)

    def extend_initial_empty_nodes(self, graph_db: bool = True):
        """
        Iterate over the first node to check if it has information, if do not, search for it on its successors

        :param graph_db: flag for storing the relation into the graph database. Default True.
        :type graph_db: bool
        :return:
        """
        last_relation = {}
        passed_nodes = []
        # Iterate over the graph by source-destination pair
        for u, v in self._graph.edges:
            # Append the source node
            passed_nodes.append(u)
            # Retrieve relation information
            relation = self._graph.get_edge_data(u, v)
            # Check non-default values of the relation
            default_keys = [k for k, v in relation.items() if k in DEFAULT_WAYS_VALUES and
                            v == DEFAULT_WAYS_VALUES[k]]
            # Check default keys -> If there are the ones specified it means it is unchanged
            while default_keys == ['slope', 'maxspeed', 'lanes', 'highway', 'name', 'surface']:
                # Retrieve new successor
                successors = list(self._graph.successors(v))
                # There are successors
                if successors:
                    # Get new relation value
                    relation = self._graph.get_edge_data(v, successors[0])
                    # Check non-default values of the relation
                    default_keys = [k for k, v in relation.items() if k in DEFAULT_WAYS_VALUES and
                                    v == DEFAULT_WAYS_VALUES[k]]
                # Append target to passed nodes
                passed_nodes.append(v)
                # Update last_relation variable
                last_relation = relation
                # Update target to its successor
                v = successors[0]
            # Once a node with non-default values is achieved, stop searching
            break

        # Iterate over the passed nodes
        for u, v in zip(passed_nodes[:-1], passed_nodes[1:]):
            relation = self._graph.get_edge_data(u, v)
            # Get those attributes that are empty or with default values and update from previous
            for key, value in relation.items():
                # Way ID, distance, congestion and slope are not copied
                if key != 'way_id' and key != 'congestion' and key != 'distance' and key != 'slope':
                    relation[key] = last_relation[key]
                else:
                    # Remain the same value as previous
                    relation[key] = value

            # Update relation data
            self._graph.add_edge(u, v, **relation)

            if graph_db:
                # Update database information
                self._graph_db.create_update_relation(relation={'from': u, 'to': v}, segment_info=relation)

    def extend_relation_info(self, source, target, previous_relation: dict) -> dict:
        """
        Extend relation information based on the previous relation

        :param source: source node
        :param target: target node
        :param previous_relation: previous relation information
        :type previous_relation: dict
        :return: updated relation information
        :rtype: dict
        """
        # Retrieve relation information
        relation = self._graph.get_edge_data(source, target)

        # Get those attributes that are empty or with default values and update from previous
        for key, value in relation.items():
            # Way ID not processed and congestion will be processed afterwards
            if key != 'way_id' and key != 'congestion':
                if value == DEFAULT_WAYS_VALUES[key]:
                    if key in previous_relation:
                        relation[key] = previous_relation[key]
            else:
                # Remain the same the way id
                relation[key] = value

        return relation

    def extend_congestion_data(self, source, target, relation: dict) -> dict:
        """
        Extend traffic congestion info based on the adjacent congestion info

        :param source: source node
        :param target: destination node
        :param relation: information related to the connection
        :type relation: dict
        :return: updated relation dict with new congestion info
        :rtype: dict
        """
        # Retrieve the predecessor and successor information
        predecessors, successors = list(self._graph.predecessors(source)), list(self._graph.successors(target))

        predecessor_congestion = successor_congestion = None
        # It exists a predecessor
        if predecessors:
            # Retrieve congestion info
            predecessor_congestion = self._graph.get_edge_data(predecessors[0], source).get('congestion', None)

        # It exists a successor
        if successors:
            # Retrieve relation information
            successor_congestion = self._graph.get_edge_data(target, successors[0]).get('congestion', None)

        # Both predecessor and successor
        if predecessor_congestion is not None and relation['congestion'] is None \
                and successor_congestion is not None:
            # print("Both predecessor and successor")
            # Calculate the mean by now
            relation['congestion'] = (predecessor_congestion + successor_congestion) // 2  # Floor
        # Only predecessor congestion information
        elif predecessor_congestion is not None and relation['congestion'] is None \
                and successor_congestion is None:
            # print("Only predecessor congestion information")
            relation['congestion'] = predecessor_congestion
        # Only successor congestion information
        elif predecessor_congestion is None and relation['congestion'] is None \
                and successor_congestion:
            # print("Only successor congestion information")
            relation['congestion'] = successor_congestion
        return relation

    def stop_engine(self):
        """
        Stop engine connections

        :return: None
        """
        self._graph_db.close()

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
    def osm_retriever(self):
        """
        Getter of OSM retriever

        :return: OSM retriever
        """
        return self._osm_retriever

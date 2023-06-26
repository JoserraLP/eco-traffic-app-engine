from dataclasses import asdict

import networkx as nx
import pandas as pd
from geopy.distance import geodesic as gd

from eco_traffic_app_engine.graph.db.neo4j import GraphDB
from eco_traffic_app_engine.graph.models import Node, Road
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

        # Clean up the network database
        self._graph_db.clear_database()

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
        if node_info.name not in self._graph.nodes:
            # Add node
            self._graph.add_node(node_info.name, lat=node_info.lat, lon=node_info.lon, height=node_info.height)

            # Check if it is required to store in the graph database
            if graph_db:
                self._graph_db.create_node(asdict(node_info))

    def create_relation(self, source_id: str, destination_id: str, road_info: Road, graph_db: bool = True) -> None:
        """
        Create a relation between source and destination nodes in the memory graph and/or graph database

        :param source_id: source node identifier
        :type source_id: str
        :param destination_id: destination node identifier
        :type destination_id: Node
        :param road_info: road information
        :type road_info: Road
        :param graph_db: flag for storing the relation into the graph database. Default True.
        :type graph_db: bool
        :return: None
        """
        # Store relation
        self._graph.add_edge(source_id, destination_id, slope=road_info.slope, distance=road_info.distance,
                             congestion=road_info.congestion, maxspeed=road_info.maxspeed, lanes=road_info.lanes,
                             highway=road_info.highway, name=road_info.name, surface=road_info.surface,
                             way_id=road_info.way_id)
        # Check if it is required to store in the graph database
        if graph_db:
            self._graph_db.create_update_relation({'from': source_id, 'to': destination_id},
                                                  road_info=asdict(road_info))

    def get_road_info(self, source_info: Node, destination_info: Node) -> Road:
        """
        Retrieve road information from different data sources

        :param source_info: source node information
        :type source_info: Node
        :param destination_info: destination node information
        :type destination_info: Node

        :return: road information
        :rtype: Road
        """
        # Calculate distance between source and destination
        distance = gd((source_info.lat, source_info.lon), (destination_info.lat, destination_info.lon)).meters

        # Get the road info based on the source and destination nodes
        source_additional_info = self._osm_retriever.get_osm_way_info(source_info.name)
        destination_additional_info = self._osm_retriever.get_osm_way_info(destination_info.name)

        # Single element -> Non junction
        if len(source_additional_info) == 1:
            way_id = source_additional_info[0]['id']
            way_info = source_additional_info[0]['tags']
        else:
            # Iterate over the nodes instead of getting the id
            source_ways_nodes = {item['id']: item['nodes'] for item in source_additional_info}
            destination_ways_nodes = {item['id']: item['nodes'] for item in destination_additional_info}

            way_id = None
            for source_id, source_nodes in source_ways_nodes.items():
                for destination_id, destination_nodes in destination_ways_nodes.items():
                    if set(source_nodes) & set(destination_nodes):
                        way_id = source_id

            way_index = None
            # Iterate over the source nodes
            for index, item in enumerate(source_additional_info):
                if item['id'] == way_id:
                    way_index = index

            # Get by index if exists, otherwise leave empty and it will be extended later
            if way_index and 'tags' in source_additional_info[way_index]:
                way_info = source_additional_info[way_index]['tags']
            else:
                way_info = {}

        maxspeed = way_info.get('maxspeed', DEFAULT_WAYS_VALUES['maxspeed'])
        lanes = way_info.get('lanes', DEFAULT_WAYS_VALUES['lanes'])
        highway = way_info.get('highway', DEFAULT_WAYS_VALUES['highway'])
        name = way_info.get('name', DEFAULT_WAYS_VALUES['name'])
        surface = way_info.get('surface', DEFAULT_WAYS_VALUES['surface'])

        if not self._osm_retriever.is_in_roundabout(source_info.name) or \
                not self._osm_retriever.is_in_roundabout(destination_info.name):
            slope = (destination_info.height - source_info.height) * 100 / distance
        else:
            slope = DEFAULT_WAYS_VALUES['slope']

        return Road(slope=slope, distance=distance, congestion=None, maxspeed=maxspeed, lanes=lanes, highway=highway,
                    name=name, surface=surface, way_id=way_id)

    def get_nodes_from_route(self, route: dict) -> list:
        """

        :param route:
        :return:
        """

        # Get legs to retrieve order of the nodes
        route_nodes = route['legs'][0]['annotation']['nodes']

        # Remove non-intersection values
        nodes = self._osm_retriever.remove_non_intersections_nodes(route_nodes)

        # Remove roundabouts
        # nodes = [node for node in nodes if not is_in_roundabout(node)]

        return nodes

    def process_routes(self):
        """
        Process all the routes and store them into the graphs

        :return:
        """
        for route in self._routes:
            # Retrieve nodes from the routes
            nodes = self.get_nodes_from_route(route)

            # String for overpassQL
            print('\n'.join([f"node(id:{item});" for item in nodes]))

            self.process_nodes_relations(nodes=nodes)

    def process_nodes_relations(self, nodes: list):
        """
        Process and create nodes and relations on the graph

        :param nodes: list of OSM nodes
        :type nodes: list
        :return:
        """
        # Retrieve node info from first element
        node_info = self._osm_retriever.get_osm_node_info(nodes[0])
        # Create given node
        self.create_node(node_info)
        # Define variable to update the source based on distance conditions
        new_source = None
        # Iterate over the nodes in packs of two
        for source, destination in zip(nodes[:-1], nodes[1:]):

            # Update source to previous value if exists
            source = new_source if new_source else source

            # Retrieve node info
            destination_node_info = self._osm_retriever.get_osm_node_info(destination)
            source_node_info = self._osm_retriever.get_osm_node_info(source)

            # Get road info to check distance
            road_info = self.get_road_info(source_node_info, destination_node_info)

            if road_info.distance < MIN_DISTANCE_NODES:
                # When distance is lower, retrieve new source
                new_source = source if new_source is None else new_source
            elif road_info.distance > MAX_DISTANCE_NODES:
                # When distance is higher, calculate intermediate nodes
                # Define number of iterations
                iterations = int(road_info.distance // MIN_DISTANCE_NODES)  # Floor
                # Calculate distance of each iteration
                it_distance = road_info.distance / iterations

                # Define source and destination per iteration (index for slicing and value)
                it_source = source
                it_source_info = source_node_info
                # Retrieve index of destination iteration
                it_dest_idx = nodes.index(destination)
                for i in range(iterations - 1):
                    # Retrieve index of source iteration
                    it_source_idx = nodes.index(it_source)

                    # Obtain the node with the minimum distance from the list of selected nodes
                    # (in the interval from it_source_idx and  it_dest_idx)
                    # The key parameter is the condition to get the minimum which is:
                    # For each element of the list, calculate the distance between it_source and the element, minus the
                    # it_distance
                    # GD (source_coords , destination_coords)
                    mid_point = min(nodes[it_source_idx:it_dest_idx],
                                    key=lambda x: abs((gd((it_source_info.lat, it_source_info.lon),
                                                          (self._osm_retriever.get_osm_node_info(x).lat,
                                                           self._osm_retriever.get_osm_node_info(x).lon)
                                                          ).meters) - it_distance))

                    # If there is no point closer than the source, the loop ends
                    if it_source == mid_point:
                        break
                    # Get middle point information
                    mid_point_info = self._osm_retriever.get_osm_node_info(mid_point)

                    # If the loop continues, the new point is created with the relation
                    self.create_node(mid_point_info)
                    self.create_relation(it_source, mid_point, self.get_road_info(it_source_info, mid_point_info))

                    # Source node is updated to the last inserted
                    it_source = mid_point
                    it_source_info = mid_point_info

                # Destination node and the road are inserted
                self.create_node(destination_node_info)
                self.create_relation(it_source, destination, self.get_road_info(it_source_info, destination_node_info))
                new_source = None

            else:
                # Otherwise there is no problem with the distance, create node and relation as it is
                self.create_node(destination_node_info)
                self.create_relation(source, destination, road_info)
                new_source = None

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
                # Add congestion to road relation between source and destination
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
        request_congestion_data(congestion_center_nodes_str)

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
                self._graph_db.create_update_relation(relation={'from': u, 'to': v}, road_info=relation)

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
                self._graph_db.create_update_relation(relation={'from': u, 'to': v}, road_info=relation)

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

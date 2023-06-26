from neomodel import db, clear_neo4j_database, config
from neomodel.contrib.spatial_properties import NeomodelPoint

from eco_traffic_app_engine.graph.db.models import Node, Road


class GraphDB:
    """
    Network topology class connection to Neo4J database

    :param ip_address: database IP address
    :type ip_address: str
    :param user: database user
    :type user: str
    :param password: database user password
    :type password: str
    """

    def __init__(self, ip_address: str, user: str, password: str):
        # Configure Neomodel database connection
        config.DATABASE_URL = f'bolt://{user}:{password}@{ip_address}'
        # Store the database
        self._db = db
        # Set the connection to the database
        self._db.set_connection(config.DATABASE_URL)

    def close(self) -> None:
        """
        Close connection to database

        :return: None
        """
        self._db.driver.close()

    def clear_database(self) -> None:
        """
        Clear database information

        :return: None
        """
        clear_neo4j_database(self._db)

    # CREATE METHODS
    @staticmethod
    def create_node(node: dict) -> None:
        """
        Create a node in the network

        :param node: node information
        :type node: dict
        :return: None
        """
        Node(name=node['name'], geospatial_point=NeomodelPoint(latitude=node['lat'], longitude=node['lon'],
                                                               height=node['height'], crs='wgs-84-3d')).save()

    @staticmethod
    def create_update_relation(relation: dict, road_info: dict) -> None:
        """
        Create/Update a relationship in the network

        :param relation: relation information
        :type relation: dict
        :param road_info: road additional information
        :type road_info: dict
        :return: None
        """
        source = Node.nodes.get(name=relation['from'])
        target = Node.nodes.get(name=relation['to'])
        # If they are not connected create the relation
        if not source.road_to.is_connected(target):
            source.road_to.connect(target, Road(**road_info).__dict__).save()
        # Otherwise update existing relation
        else:
            # Get road relationship between nodes
            rel = source.road_to.relationship(target)
            # Iterate over the attributes
            for k, v in road_info.items():
                # A dict update is not possible
                setattr(rel, k, v)
            # Save the relation in the database
            rel.save()

    @staticmethod
    def update_road_congestion(source: str, target: str, congestion: int) -> None:
        """
        Update the congestion value for the road connecting source and target

        :param source: source node identifier
        :type source: str
        :param target: target node identifier
        :type target: str
        :param congestion: congestion value
        :type congestion: int

        :return: None
        """
        # Get source and target
        source = Node.nodes.get(name=source)
        target = Node.nodes.get(name=target)

        # Get relation between nodes
        relation = source.road_to.relationship(target)

        # Update relation congestion
        relation.congestion = congestion

        # Save the relation in the database
        relation.save()

from dataclasses import dataclass

from eco_traffic_app_engine.static.constants import DEFAULT_WAYS_VALUES


@dataclass
class Road:
    """ OpenStreetMap road relation between two nodes """
    way_id: str = ""
    distance: float = DEFAULT_WAYS_VALUES['distance']
    slope: float = DEFAULT_WAYS_VALUES['slope']
    maxspeed: float = DEFAULT_WAYS_VALUES['maxspeed']
    lanes: int = DEFAULT_WAYS_VALUES['lanes']
    highway: str = DEFAULT_WAYS_VALUES['highway']
    name: str = DEFAULT_WAYS_VALUES['name']
    surface: str = DEFAULT_WAYS_VALUES['surface']
    congestion: int = DEFAULT_WAYS_VALUES['congestion']


@dataclass
class Node:
    """ OpenStreetMap node information """
    name: str
    lat: float
    lon: float
    height: float

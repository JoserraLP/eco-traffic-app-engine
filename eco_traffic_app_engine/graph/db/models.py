from neomodel import StructuredNode, StructuredRel, IntegerProperty, RelationshipTo, \
    FloatProperty, StringProperty
from neomodel.contrib.spatial_properties import PointProperty

from eco_traffic_app_engine.static.constants import DEFAULT_WAYS_VALUES


# Relationships
class Road(StructuredRel):
    """ OpenStreetMap road relation between two nodes """
    way_id = StringProperty(default="")
    distance = FloatProperty(default=DEFAULT_WAYS_VALUES['distance'])
    slope = FloatProperty(default=DEFAULT_WAYS_VALUES['slope'])
    maxspeed = FloatProperty(default=DEFAULT_WAYS_VALUES['maxspeed'])
    lanes = IntegerProperty(default=DEFAULT_WAYS_VALUES['lanes'])
    highway = StringProperty(default=DEFAULT_WAYS_VALUES['highway'])
    name = StringProperty(default=DEFAULT_WAYS_VALUES['name'])
    surface = StringProperty(default=DEFAULT_WAYS_VALUES['surface'])
    congestion = StringProperty(default=DEFAULT_WAYS_VALUES['congestion'])


# Nodes
class Node(StructuredNode):
    """ OpenStreetMap node information """
    name = IntegerProperty(unique_index=True, required=True)
    geospatial_point = PointProperty(crs='wgs-84-3d', required=True)
    road_to = RelationshipTo("Node", "ROAD_TO", model=Road)

from neomodel import StructuredNode, StructuredRel, IntegerProperty, RelationshipTo, \
    FloatProperty, StringProperty
from neomodel.contrib.spatial_properties import PointProperty

from eco_traffic_app_engine.static.constants import DEFAULT_WAYS_VALUES


# Relationships
class Segment(StructuredRel):
    """ Segment relation between two nodes """
    way_id = StringProperty(default="")
    distance = FloatProperty(default=DEFAULT_WAYS_VALUES['distance'])
    slope = FloatProperty(default=DEFAULT_WAYS_VALUES['slope'])
    max_speed = FloatProperty(default=DEFAULT_WAYS_VALUES['max_speed'])
    lanes = IntegerProperty(default=DEFAULT_WAYS_VALUES['lanes'])
    highway = StringProperty(default=DEFAULT_WAYS_VALUES['highway'])
    name = StringProperty(default=DEFAULT_WAYS_VALUES['name'])
    surface = StringProperty(default=DEFAULT_WAYS_VALUES['surface'])
    congestion = StringProperty(default=DEFAULT_WAYS_VALUES['congestion'])


# Nodes
class Node(StructuredNode):
    """ Node information """
    node_id = IntegerProperty(unique_index=True, required=True)
    geospatial_point = PointProperty(crs='wgs-84-3d', required=True)
    segment_to = RelationshipTo("Node", "SEGMENT_TO", model=Segment)

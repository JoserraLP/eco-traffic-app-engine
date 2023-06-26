# Open Topo Data service
HEIGHT_API_URL = 'http://localhost:5000/v1/srtm30mspain?locations='

# Graph database
GRAPH_DB_URL = 'localhost:7687'
GRAPH_DB_USER = 'neo4j'
GRAPH_DB_PASSWORD = 'admin'

# Congestion distance
CONGESTION_DISTANCE = 500

# R script directory
R_SCRIPT_DIRECTORY = '../googletraffic/main.R'

# Congestion related data
CONGESTION_DICT = {
    "low": 0,
    "moderate": 1,
    "heavy": 2,
    "severe": 3
}

CONGESTION_DATA_DIR = '../congestion_data/'

MIN_DISTANCE_NODES = 40
MAX_DISTANCE_NODES = 80


DEFAULT_WAYS_VALUES = {
    'distance': 0.0,
    'slope': 0.0,
    'maxspeed': 0.0,
    'lanes': 1,
    'highway': '',
    'name': '',
    'surface': '',
    'congestion': None
}

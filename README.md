# Eco-Traffic APP Engine
The Eco-Traffic App Engine is the main component of the Eco-Traffic APP national project, and its functionality is 
related to the request, processing and storage of different routes between source and destination, allowing latterly to 
request the optimal route considering different metrics such as vehicle engine consumption, shortest distance, fastest, 
among others.

## File structure
This component is developed as a Python library with the following architecture:
- **engine**: the eco traffic engine itself and its functionalities.
- **graph**: all the data models used in the engine (in-memory) graph. There is also a sub-folder called "db", 
related to the connection with a graph database, its related data models and several utils, in this case Neo4j.
- **osm**: OpenStreetMap (OSM) information retrieval classes and utils.
- **others**: several utils related mainly to file processing.
- **routing**: classes for retrieving routes from several routing services.
- **static**: constants values used on the engine.
- **traffic**: real-time traffic congestion retrieval and processing functions.


There is also another folder called "cache" which stores all the information related to OSM/Overpass queries as a cache 
memory.

## Additional files
Besides, there are two folders on the project, related mainly to two different purposes:
- **googletraffic**: it stores the R library and script required to request the congestion information related to the 
 routes. 
- **congestion_data**: it stores the XLSX congestion files retrieved by the "GoogleTraffic" library. 


## Execution command

Before executing the Eco-Traffic App Engine, it is required to set as an environment variable, the API key from 
MapBoxAPI with the following command:

**Windows**:
~~~
SET MAPBOX_API_KEY="<your key>"
~~~

**Ubuntu**:
~~~
EXPORT MAPBOX_API_KEY="<your key>"
~~~

Once the environment variable has been set, we can execute the following command, on the "eco_traffic_app_engine" 
folder:
~~~
python main.py
~~~

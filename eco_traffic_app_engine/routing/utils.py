import math
from statistics import mean

import pandas as pd
import requests
from geopy.distance import geodesic as gd

from eco_traffic_app_engine.graph.models import Coords
from eco_traffic_app_engine.static.constants import HEIGHT_API_URL, MAX_DISTANCE_BETWEEN_NODES, \
    DISTANCE_BETWEEN_NEW_NODES, NOMINATIM_API_URL, NOMINATIM_ADD_PARAMS, SLOPE_THRESHOLD, BATCHING_WINDOW_SIZE, \
    SLOPE_VARIANCE_DIFFERENCE


def split_list(list_data: list, n: int):
    """
    Split a list into list of n size

    :param list_data: list with the data
    :type list_data: list
    :param n: number of items per sublist
    :type n: int
    :return:
    """
    # Iterate over the list and retrieve the requested sublist
    for i in range(0, len(list_data), n):
        yield list_data[i:i + n]


def process_route(route_coordinates: list) -> dict:
    """
    Process and segment the input route coordinates and return its related values (segments, heights, max_speed,
    distances and slopes)

    :param route_coordinates: coordinates of the input route
    :type route_coordinates: list
    :return: dictionary with the processed route (segments, heights, max_speed, distances and slopes)
    """

    # Calculate the extended coordinates along with distances
    route_extended_coordinates, distances = calculate_extended_coords_and_distances(route_coordinates)
    # Retrieve heights
    heights = retrieve_heights(route_extended_coordinates)
    # Calculate the slopes  with the distances and heights
    slopes = calculate_slopes(distances, heights)
    # Retrieve maximum speed and additional information
    max_speeds, add_info = retrieve_max_speeds(route_extended_coordinates)

    # Retrieve indices for segmented route
    indices = segment_route(max_speeds, slopes)

    # Calculate sum of distances of the non-selected nodes
    sum_distances_segment = [sum(distances[i:j]) for i, j in zip(indices,
                                                                 indices[1:])]

    # Calculate mean of slopes of the non-selected nodes
    mean_slope_segment = [mean(slopes[i:j]) for i, j in zip(indices,
                                                            indices[1:])]

    # return the segments, heights, maximum speeds, distances and slopes
    return {'segments': [route_extended_coordinates[i] for i in indices],
            'heights': [heights[i] for i in indices],
            'max_speed': [max_speeds[i] for i in indices][:-1],
            # Last item of max speed removed as it is not used
            'distances': sum_distances_segment,
            'slopes': mean_slope_segment}


def calculate_extended_coords_and_distances(route_coordinates: list):
    """
    Calculate the extended route (with additional coordinates) along with its distances between nodes

    :param route_coordinates: input route coordinates
    :type route_coordinates: list
    :return: list of coordinates of extended route and its distances
    """

    # Create list for extended nodes and distances
    route_extended_coordinates, distances = [], []

    # Define destination as None
    destination = None

    # Iterate over the nodes in packs of two
    for source, destination in zip(route_coordinates, route_coordinates[1:]):
        # Calculate distance between source and destination
        distance = gd((source.lon, source.lat), (destination.lon, destination.lat)).meters

        # Add source node to extended route
        route_extended_coordinates.append(source)

        # If distance greater than threshold
        if distance > MAX_DISTANCE_BETWEEN_NODES:
            # Calculate intermediate coords
            intermediate_coords, num_segments = calculate_intermediate_coords(source, destination, distance)

            # Append intermediate coords
            route_extended_coordinates += intermediate_coords
            # Calculate distance -> It is equal for each segment
            intermediate_distance = distance / (num_segments - 1)
            # Append intermediate distances
            distances += [intermediate_distance] * (num_segments - 1)

        # Append the distance
        distances.append(distance)

    # Add destination node outside the loop as it is the last element
    route_extended_coordinates.append(destination)

    return route_extended_coordinates, distances


def retrieve_heights(route_coordinates: list[Coords]) -> list:
    """
    Retrieve heights values of the input route coordinates

    :param route_coordinates: input route coordinates
    :type route_coordinates: list[Coords]
    :return: list with associated heights
    :rtype: list
    """
    split_coordinates = list(split_list(route_coordinates, n=1001))

    heights = []
    # Iterate over the list coordinates
    for inner_list in split_coordinates:
        # Append the coordinates to the query
        request_str = HEIGHT_API_URL + '|'.join(f'{item.lat},{item.lon}' for item in inner_list)

        # Perform request and parse to json
        results = requests.get(url=request_str).json()

        # Append heights results to list
        heights += [result['elevation'] for result in results['results']]

    return heights


def calculate_slopes(distances: list, heights: list) -> list:
    """
    Calculate the slopes of the segments based on the distance and heights of the coordinates

    :param distances: distances of the route segments
    :type distances: list
    :param heights: heights of the route segments
    :type heights: list
    :return: list with the slope segments
    :rtype: list
    """
    # Create a dataframe with the distances, heights
    df = pd.DataFrame(list(zip(distances, heights)), columns=['distance', 'height'])
    # Create a column with mean of heights with the window size -> use a rolling function with "center"
    # flag to enable next and previous values
    df['mean_height'] = df['height'].rolling(BATCHING_WINDOW_SIZE, center=True).mean()

    # Create a column with distance traveled -> Iterate over a loop
    distance_traveled = [0]
    for i in range(1, len(df)):
        # distance_traveled[i] = 0.5*(speed_m_s[i] + speed_m_s[i-1]) + distance_traveled[i-1]
        distance_traveled.append(0.5 * (df.loc[i, 'distance'] + df.loc[i - 1, 'distance']) + distance_traveled[i - 1])
    # Store the list
    df['distance_traveled'] = distance_traveled

    # Create a column with the slope -> Iterate over a loop
    slope = [0]
    for i in range(1, len(df)):
        # Calculate difference of heights
        height_difference = df.loc[i, 'mean_height'] - df.loc[i - 1, 'mean_height']
        # Calculate difference of distance traveled
        distance_traveled_difference = df.loc[i, 'distance_traveled'] - df.loc[i - 1, 'distance_traveled']

        # Check the difference of distance traveled is valid
        if distance_traveled_difference != 0:
            slope.append((height_difference / distance_traveled_difference) * 100)
        else:
            # Otherwise set 0
            slope.append(0)

    # Store the list
    df['slope'] = slope
    # Replace slope NaN values with 0
    df['slope'] = df['slope'].fillna(0)
    # Limit the values of the slope based on a realistic range
    df['slope'] = df['slope'].clip(lower=-SLOPE_THRESHOLD, upper=SLOPE_THRESHOLD)

    return list(df['slope'])


def retrieve_max_speeds(route_coordinates: list[Coords]):
    """
    Retrieve maximum speeds related to the route coordinates

    :param route_coordinates: all the route coordinates
    :type route_coordinates: list of Coords

    :return: maximum speed list along with additional information for each coordinate
    """
    max_speeds, add_info = [], []

    for coordinates in route_coordinates:
        # Append the coordinates to the query
        request_str = NOMINATIM_API_URL + "lat=" + str(coordinates.lat) + "&lon=" + str(
            coordinates.lon) + NOMINATIM_ADD_PARAMS

        # Perform request and parse to json
        results = requests.get(url=request_str).json()

        if 'extratags' in results:
            extratags = results['extratags']

            # Append maximum speed value or -1 by default
            max_speeds.append(int(extratags.pop('maxspeed')) if 'maxspeed' in extratags else -1)

            # Append additional info
            add_info.append(results['extratags'])
        else:
            # Append -1 as there is no information
            max_speeds.append(-1)

    # Process and extend maximum speed info -> Extend from previous info
    for i in range(len(max_speeds) - 2):
        # Get current and next speed
        cur_max_speed = max_speeds[i]
        next_max_speed = max_speeds[i + 1]
        # Check if default value to extend it from previous value
        if next_max_speed == -1:
            max_speeds[i + 1] = cur_max_speed

    return max_speeds, add_info


def segment_route(max_speeds: list, slopes: list) -> list:
    """
    Segment the route by selecting only those coordinates (by index) where there is a difference of maximum speeds
    or slopes on adjacent nodes

    :param max_speeds: maximum speeds per a pair of coordinates
    :type max_speeds: list
    :param slopes: slopes per a pair of coordinates
    :type slopes: list

    :return: list with the indices of segmented route
    """
    # First remove the last maximum speed item as it will not be used. One more item than slopes
    max_speeds = max_speeds[:-1]

    # Valid indices (values varies)
    indices = [0]

    # We can iterate on any of the two list as their size is the same
    for i in range(1, len(max_speeds)):
        # Check if values are different
        if max_speeds[i] != max_speeds[i - 1] or abs(slopes[i] - slopes[i - 1]) > SLOPE_VARIANCE_DIFFERENCE:
            indices.append(i)

    return indices


def calculate_intermediate_coords(source: Coords, destination: Coords, distance: float):
    """
    Calculate intermediate coordinates

    :param source: Source coordinates
    :type source: Coords
    :param destination: Destination coordinates
    :type destination: Coords
    :param distance: distance between the source and destination
    :type distance: float
    :return: list with intermediate coords and the number of segments
    """
    # Initialize intermediate coords list
    intermediate_coords = []
    # Calculate the difference of longitude and latitude (destination-source)
    delta_lon = destination.lon - source.lon
    delta_lat = destination.lat - source.lat
    # Calculate the number of segments
    num_segments = math.ceil(distance / DISTANCE_BETWEEN_NEW_NODES)
    # Calculate the proportion per each segment
    delta_t = 1 / num_segments
    # Multiply longitude and latitude by the proportion
    cons_lon = delta_lon * delta_t
    cons_lat = delta_lat * delta_t

    # Store actual longitude and latitude
    lon_act = source.lon
    lat_act = source.lat

    # Iterate over the segmentes
    for i in range(num_segments - 1):
        # Sum actual values with the constant
        lon_act += cons_lon
        lat_act += cons_lat
        # Append intermediate coords
        intermediate_coords.append(Coords(lat=lat_act, lon=lon_act))

    return intermediate_coords, num_segments

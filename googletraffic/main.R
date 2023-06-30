## Setup
## Load package
library(googletraffic)
library(ggplot2)
library(raster)
library(mapboxapi)
library(dplyr)
library(leaflet)
library(sf)

# Define zoom
zoom <- 15

# Get input parameters
coordinates_list <- strsplit(coordinates, ";")[[1]]

# Create empty dataframe
congestion_data <- data.frame(class = character(0), congestion = character(0), 
                              geometry = character(0),
                              stringsAsFactors = FALSE)

## Set API key
mapbox_key <- Sys.getenv(x = "MAPBOX_API_KEY")

# Iterate over pair of items
for (coordinates_pair in coordinates_list) {
  # Get pair of coordinates and create a vector
  pair <- strsplit(coordinates_pair, ",")[[1]]
  location <- c(as.numeric(pair[2]), as.numeric(pair[1]))
  
  # Request for data
  coordinates_congestion <- get_vector_tiles(
    tileset_id = "mapbox.mapbox-traffic-v1",
    location = location, # c(longitude, latitude)
    zoom = zoom,
    access_token = mapbox_key
  )$traffic$lines
  
  if (!is.null(coordinates_congestion)) {
  
    # Select only valid data (class, congestion and geometry)
    df <- select(as.data.frame(coordinates_congestion), 'class', 'congestion', 
                 'geometry')
    
    # Append to dataframe
    congestion_data <- rbind(congestion_data, df)
  }
}

print(congestion_data)

## STORE INFO INTO XLSX
# First set the environment variable
Sys.setenv(JAVA_HOME="C:\\Program Files\\Java\\jre-1.8") # for 64-bit version
library(xlsx)  

# Select only valid data
df <- select(as.data.frame(congestion_data), 'class', 'congestion', 'geometry')

# Parse geometry to valid type -> character is the only valid one but need to be
# processed afterwards
df$geometry <- as.character(df$geometry)

# Get current date
cur_date <- format(Sys.time(), "%d_%m_%Y__%H_%M_%S")

# Write output dataframe
write.xlsx(df, paste('../congestion_data/', cur_date, '.xlsx', sep=""))

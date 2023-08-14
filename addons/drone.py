import json
import time
import requests
import math


description = "Control the drone, move(distance(meter), direction(north, south, east, west)) example: move(5, 'east')"
parameters = {
    "type": "object",
    "properties": {
        "instruction": {
            "type": "string",
            "description": "The instruction to the drone: move",
        },
        "parameters": {
            "type": "string",
            "description": "The parameters to the drone instruction",
        }
    },
    "required": ["instruction", "parameters"],
}

import requests

def drone(instruction, parameters):
    url = "http://localhost:8000/api/vehicle/3/llm/command"
    headers = {'Content-Type': 'text/plain'}

    if instruction == "move":
        lat, long = move({parameters})
        data = f"move_to({lat}, {long})"
    
    response = requests.put(url, data=data, headers=headers)
    return response.text

def get_state():
    url = "http://127.0.0.1:8000/api/vehicle/3/llm/state"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return "Failed to get state"

def move(distance, direction):
    # Get the current state
    state = get_state()
    if isinstance(state, str):
        print(state)
        return

    # Extract the current lat and lon
    current_lat = state['position_geo'][0]
    current_lon = state['position_geo'][1]

    # Convert distance from meters to degrees
    distance_in_degrees = distance / 111320

    # Determine the new lat and lon based on the direction
    if direction.lower() == 'north':
        new_lat = current_lat + distance_in_degrees
        new_lon = current_lon
    elif direction.lower() == 'south':
        new_lat = current_lat - distance_in_degrees
        new_lon = current_lon
    elif direction.lower() == 'east':
        new_lat = current_lat
        new_lon = current_lon + distance_in_degrees
    elif direction.lower() == 'west':
        new_lat = current_lat
        new_lon = current_lon - distance_in_degrees
    else:
        print("Invalid direction")
        return

    return new_lat, new_lon

# Call the function to move east
#move(5, 'east')

# while True:
#     print(get_state())
#     instruction = input("Instruction: ")
#     parameters = input("Parameters: ")
#     print(drone(instruction, parameters))
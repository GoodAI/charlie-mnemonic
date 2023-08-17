import json
import time
import requests
import math


description = "Control drones, move(distance(meter), direction(n, s, e, w, ne, nw, se, sw)) example: move(5, 'e'), set_pause_on_detection(True/False), set_follow_on_detection(True/False), start_mission(mission_name), return_home(), resume_mission()), pause_mission(), and take_off(meters) "
parameters = {
    "type": "object",
    "properties": {
        "drone": {
            "type": "number",
            "description": "The drone number, example: 3",
        },
        "instruction": {
            "type": "string",
            "description": "The instruction to the drone, example: move",
        },
        "parameters": {
            "type": "string",
            "description": "The parameters, comma seperate, example: 5, 'e'",
        }
    },
    "required": ["instruction", "parameters"],
}

import requests

def str_to_bool(s):
    if s.lower() == 'true':
        return True
    elif s.lower() == 'false':
        return False
    else:
        raise ValueError("Cannot convert {} to a bool".format(s))

def drone(drone, instruction, parameters):
    url = f"http://localhost:8000/api/vehicle/{drone}/llm/command"
    headers = {'Content-Type': 'text/plain'}

    print(instruction)
    print(parameters)

    if instruction == "move":
        parameters_list = parameters.split(',')
        if len(parameters_list) != 2:
            return "Invalid parameters, need 2 parameters, distance and direction"
        distance = int(parameters_list[0])
        direction = parameters_list[1].strip().strip("'")
        lat, long = move(drone, distance, direction)
        data = f"move_to({lat}, {long})"
    elif instruction == "move_coods":
        parameters_list = parameters.split(',')
        if len(parameters_list) != 2:
            return "Invalid parameters, need 2 parameters, distance and direction"
        lat = int(parameters_list[0].strip())
        long = int(parameters_list[1].strip())
        data = f"move_to({lat}, {long})"
    elif instruction == "set_pause_on_detection":
        pause = str_to_bool(parameters)
        data = f"set_pause_on_detection({pause})"
    elif instruction == "set_follow_on_detection":
        follow = str_to_bool(parameters)
        data = f"set_follow_on_detection({follow})"
    elif instruction == "start_mission":
        mission_name = parameters
        data = f"start_mission({mission_name})"
    elif instruction == "return_home":
        data = "return_home()"
    elif instruction == "resume_mission":
        data = "resume_mission()"
    elif instruction == "pause_mission":
        data = "pause_mission()"
    elif instruction == "take_off" or instruction == "takeoff":
        data = "take_off(5)"

    
    response = requests.put(url, data=data, headers=headers)
    return response.text

def get_state(drone):
    url = f"http://127.0.0.1:8000/api/vehicle/{drone}/llm/state"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return "Failed to get state"

def move(drone, distance, direction):
    # Get the current state
    state = get_state(drone)
    if isinstance(state, str):
        print(state)
        return

    # Extract the current lat and lon
    current_lat = state['position_geo'][0]
    current_lon = state['position_geo'][1]

    # Convert distance from meters to degrees
    distance_in_degrees = distance / 111320

    # Determine the new lat and lon based on the direction
    if direction.lower() == 'n' or direction.lower() == 'north':
        new_lat = current_lat + distance_in_degrees
        new_lon = current_lon
    elif direction.lower() == 's' or direction.lower() == 'south':
        new_lat = current_lat - distance_in_degrees
        new_lon = current_lon
    elif direction.lower() == 'e' or direction.lower() == 'east':
        new_lat = current_lat
        new_lon = current_lon + distance_in_degrees
    elif direction.lower() == 'w' or direction.lower() == 'west':
        new_lat = current_lat
        new_lon = current_lon - distance_in_degrees
    elif direction.lower() == 'ne' or direction.lower() == 'northeast':
        new_lat = current_lat + (distance_in_degrees / 2 ** 0.5)
        new_lon = current_lon + (distance_in_degrees / 2 ** 0.5)
    elif direction.lower() == 'nw' or direction.lower() == 'northwest':
        new_lat = current_lat + (distance_in_degrees / 2 ** 0.5)
        new_lon = current_lon - (distance_in_degrees / 2 ** 0.5)
    elif direction.lower() == 'se' or direction.lower() == 'southeast':
        new_lat = current_lat - (distance_in_degrees / 2 ** 0.5)
        new_lon = current_lon + (distance_in_degrees / 2 ** 0.5)
    elif direction.lower() == 'sw' or direction.lower() == 'southwest':
        new_lat = current_lat - (distance_in_degrees / 2 ** 0.5)
        new_lon = current_lon - (distance_in_degrees / 2 ** 0.5)
    else:
        print("Invalid direction")
        return

    return new_lat, new_lon

# while True:
#     print(get_state(3))
#     instruction = input("Instruction: ")
#     parameters = input("Parameters: ")
#     print(drone(3, instruction, parameters))

# def tryit():
#     drone = 3
#     url = f"http://localhost:8000/api/vehicle/{drone}/llm/command"
#     headers = {'Content-Type': 'text/plain'}
#     data = 'move_to(50.088656, 14.373172)'
#     response = requests.put(url, data=data, headers=headers)
#     print(response.json())

# tryit()

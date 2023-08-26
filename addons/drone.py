import json
import asyncio
import math
from geopy.distance import geodesic
from aiohttp import ClientSession

description = "Control drones, move(distance(meter), direction(degrees)) example: move(5, 90), move_to(lat, long), set_pause_on_detection(True/False), set_follow_on_detection(True/False), start_mission(mission_name), return_home(), resume_mission()), pause_mission(), take_off(meters), execute_instructions(instructions_list) example: execute_instructions([move(10,0), rotate_by(45) move(20,0)]), rotate_by(heading, speed), rotate_to(heading, speed), rotate_gimbal_to(angle), get_state(), look_at(lat, long)"
parameters = {
    "type": "object",
    "properties": {
        "drones": {
            "type": "array",
            "items": { "type": "number" },
            "description": "The drone numbers, example: [3, 4]",
        },
        "instruction": {
            "type": "string",
            "description": "The instruction to the drone, example: move",
        },
        "parameters": {
            "type": "string",
            "description": "The parameters, comma separate, example: 5, 90",
        }
    },
    "required": ["drone", "instruction", "parameters"],
}

def str_to_bool(s):
    if s.lower() == 'true':
        return True
    elif s.lower() == 'false':
        return False
    else:
        raise ValueError("Cannot convert {} to a bool".format(s))

async def drone(drones, instruction, parameters):
    try:
        return await run_drone(drones, instruction, parameters)
    except TypeError as e:
        return f"Error: {e}"

async def run_drone(drones, instruction, parameters):
    tasks = []
    for drone in drones:
        try:
            url = f"http://localhost:8000/api/vehicle/{drone}/llm/command"
            headers = {'Content-Type': 'text/plain'}

            print(instruction)
            print(parameters)

            if instruction == "move":
                if isinstance(parameters, str):
                    parameters_list = parameters.split(',')
                else:
                    parameters_list = parameters
                if len(parameters_list) != 2:
                    return "Invalid parameters, need 2 parameters, distance and direction"
                distance = int(parameters_list[0])
                direction = int(parameters_list[1].strip())
                lat, long = await move(drone, distance, direction)
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
                data = f"take_off({parameters})"
            elif instruction == "rotate":
                data = f"rotate_by({parameters})"
            elif instruction == "rotate_by":
                data = f"rotate_by({parameters})"
            elif instruction == "rotate_to":
                data = f"rotate_to({parameters})"
            elif instruction == "rotate_gimbal_to":
                data = f"rotate_gimbal_to({parameters})"
            elif instruction == "move_to":
                data = f"move_to({parameters})"
            elif instruction == "fly_path_in_shape":
                #data = f"fly_path_in_shape({parameters})"
                parameters_list = parameters.split(',')
                if len(parameters_list) != 2:
                    return "Invalid parameters, need 2 parameters, shape and size"
                shape = parameters_list[0]
                size = int(parameters_list[1].strip())
                response = await fly_path_in_shape(drone, shape, size)
                return response
            elif instruction == "execute_instructions":
                all_responses = ""
                for drone in drones:
                    instructions_list = parse_instructions(parameters)
                    response = await execute_instructions(drone, instructions_list)
                    all_responses += response + "\n"
                return all_responses
            elif instruction == "get_state":
                response = await get_state(drones)
                return response
            elif instruction == "look_at":
                data = f"look_at({parameters})"

            else:
                return "Invalid instruction"

            tasks.append(send_command(url, data, headers))
        except Exception as e:
            print(f"Error: {e}")
            return f"Error: {e}"
    
    responses = await asyncio.gather(*tasks)
    return responses

async def send_command(url, data, headers):
    async with ClientSession() as session:
        async with session.put(url, data=data, headers=headers) as response:
            return await response.text()

async def get_state_i(drone):
    '''Get the current state of a drone'''
    url = f"http://127.0.0.1:8000/api/vehicle/{drone}/llm/state"
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return "Failed to get state"
            
async def get_state(drones):
    '''Get the current state of the drones'''
    responses = ""
    for drone in drones:
        url = f"http://127.0.0.1:8000/api/vehicle/{drone}/llm/state"
        async with ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    responses += await response.text() + "\n"
                else:
                    responses += f"Error: {response.status}\n"
    return responses

async def move(drone, distance, direction):
    # Get the current state
    state = await get_state_i(drone)
    if isinstance(state, str):
        print(state)
        return

    # Extract the current lat and lon and heading
    current_lat = state['position_geo'][0]
    current_lon = state['position_geo'][1]
    current_heading = state['attitude'][0] * 180 / math.pi

    new_direction = (current_heading + direction) % 360

    # Calculate the new coordinates using the known distance and direction
    new_coords = geodesic(meters=distance).destination((current_lat, current_lon), new_direction)
    new_lat, new_lon = new_coords.latitude, new_coords.longitude

    return new_lat, new_lon

async def fly_path_in_shape(drone, shape, size):
    # Get the current state
    state = await get_state_i(drone)
    if isinstance(state, str):
        print(state)
        return

    # Extract the current lat and lon
    current_lat = state['position_geo'][0]
    current_lon = state['position_geo'][1]
    current_heading = state['attitude'][0] * 180 / math.pi

    # if the shape is a square
    if shape == "square":
        # Calculate the new coordinates using the known distance and direction
        new_direction = (current_heading + 90) % 360
        new_coords = geodesic(meters=size).destination((current_lat, current_lon), new_direction)
        new_lat, new_lon = new_coords.latitude, new_coords.longitude

        # Calculate the new coordinates using the known distance and direction
        new_direction = (current_heading + 180) % 360
        new_coords = geodesic(meters=size).destination((new_lat, new_lon), new_direction)
        new_lat, new_lon = new_coords.latitude, new_coords.longitude

        # Calculate the new coordinates using the known distance and direction
        new_direction = (current_heading + 270) % 360
        new_coords = geodesic(meters=size).destination((new_lat, new_lon), new_direction)
        new_lat, new_lon = new_coords.latitude, new_coords.longitude

        # Calculate the new coordinates using the known distance and direction
        new_direction = (current_heading + 0) % 360
        new_coords = geodesic(meters=size).destination((new_lat, new_lon), new_direction)
        new_lat, new_lon = new_coords.latitude, new_coords.longitude

        return f"fly_path_in_shape(square, {size})"
    
    else:
        return "Invalid shape, only square is supported"

import re

def parse_instructions(instructions_str):
    # Extract all commands and their parameters
    matches = re.findall(r'(\w+)\((.*?)\)', instructions_str)
    
    # Keep parameters as string
    instructions = [(command, params) for command, params in matches]
    
    return instructions


async def execute_instructions(drone, instructions_list):
    full_result = f"Drone {drone} executed instructions:\n"
    for command, params in instructions_list:
        results_list = await run_drone([drone], command, params)
        results = json.loads(results_list[0])
        print(results)
        full_result += f"{results.get('command')}, {results.get('success')}, {results.get('message')}\n"
    return full_result


# async def main():
#     # get drone 3 state
#     drone = 3
#     instr_list = "move(10, 0), rotate_by(10), move(10, 0), rotate_by(10),move(10, 0), rotate_by(10),move(10, 0), rotate_by(10),move(10, 0), rotate_by(10),"
#     instructions_list = parse_instructions(instr_list)
#     response = await execute_instructions(drone, instructions_list)
#     print(response)

# # Python 3.7+
# if __name__ == "__main__":
#     asyncio.run(main())
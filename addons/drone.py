import json
import asyncio
import math
import os
from geopy.distance import geodesic
from aiohttp import ClientSession
import requests

class DroneStateError(Exception):
    pass

description = "Control drones, move(distance(m), direction(relative degrees)) example: move(5, 20), move_by(east, north, up) # example move 50m northwest: move_by(-35.4, 35.4, 0), move_to(lat, long), set_pause_on_detection(True/False), set_follow_on_detection(True/False), start_mission(mission_name), return_home(), resume_mission(), pause_mission(), take_off(), execute_instructions(instructions_list) example: execute_instructions(start_mission(patrol), wait(10) pause_mission(), set_follow_on_detection(True)) #use this for or a chain of instructions, rotate_by(heading, speed), rotate_to(heading, speed), rotate_gimbal_to(angle), get_state(), look_at(lat, long), parallel_square(), duet(), move_to_see(lat, lon, alt), follow_object(object_id), reset_objects(), panic_button(targetId), save_drone_coords(name), save_coords(name, long, lat, alt?) # example save_coords(spotX, 50.0882423, 14.3732562, -4.634688745580661), move_to_saved(name)"
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
            "description": "The parameters, comma separate, example: 5, 90, no list or array needed",
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
    errors = []
    if not isinstance(drones, list):
        drones_list = drones.split(',')
        drones = [int(drone) for drone in drones_list]

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
                distance = int(float(parameters_list[0]))
                direction = int(float(parameters_list[1].strip()))
                result = await move(drone, distance, direction)
                if isinstance(result, str):  # if result is a string, an error occurred
                    errors.append(result)  # Add error to the list
                    continue
                lat, long = result  # if result is not a string, it should be a tuple of two values
                data = f"move_to_blocking({lat}, {long})"
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
                data = f"rotate_by_blocking({parameters})"
            elif instruction == "rotate_by":
                data = f"rotate_by_blocking({parameters})"
            elif instruction == "rotate_to":
                data = f"rotate_to_blocking({parameters})"
            elif instruction == "rotate_gimbal_to":
                data = f"rotate_gimbal_to_blocking({parameters})"
            elif instruction == "move_to":
                data = f"move_to_blocking({parameters})"
            elif instruction == "execute_instructions":
                instructions_list = parse_instructions(parameters)
                response = await asyncio.gather(
                    *(execute_instructions(drone, instructions_list) for drone in drones)
                    )
                return response
            elif instruction == "get_state":
                response = await get_state(drones)
                return response
            elif instruction == "look_at":
                data = f"look_at_blocking({parameters})"
            elif instruction == "duet":
                await duet(drones)
                return "Finished duet"
            elif instruction == "parallel_square":
                await parallel_square()
                return "Finished paralell_square"
            elif instruction == "move_to_see":
                if isinstance(parameters, str):
                    parameters_list = parameters.split(',')
                else:
                    parameters_list = parameters
                if len(parameters_list) != 3:
                    return "Invalid parameters, need 3 parameters, lat, lon and alt"
                lat = int(float(parameters_list[0]))
                lon = int(float(parameters_list[1]))
                alt = int(float(parameters_list[2].strip()))
                data = f"move_to_see_blocking({lat}, {lon}, {alt})"
            elif instruction == "follow_object":
                data = f"follow_object({parameters})"
            elif instruction == "reset_objects":
                data = "reset_objects()"
            elif instruction == "arm_drones":
                response = await asyncio.gather(
                    *(arm_drones(drone) for drone in drones)
                    )
                return response
            elif instruction == "wait":
                await asyncio.sleep(int(parameters))
                return f"Waited for {parameters} seconds"
            # elif instruction == "goodai_shape":
            #     response = await goodai_shape(drones)
            #     return response
            elif instruction == "move_by":
                if isinstance(parameters, str):
                    parameters_list = parameters.split(',')
                else:
                    parameters_list = parameters
                if len(parameters_list) != 3:
                    return "Invalid parameters, need 3 parameters, east, north and up"
                east = int(float(parameters_list[0]))
                north = int(float(parameters_list[1]))
                up = int(float(parameters_list[2].strip()))
                data = f"move_by_blocking({east}, {north}, {up})"
            elif instruction == "panic_button":
                data = f"panic_button({parameters})"
            elif instruction == "save_coords":
                response = await save_coords(parameters)
                return response
            elif instruction == "save_drone_coords":
                response = await save_drone_coords(drone, parameters)
                return response
            elif instruction == "move_to_saved":
                response = await move_to_saved(drone, parameters)
                return response
            else:
                return "Invalid instruction"

            tasks.append(send_command(url, data, headers))
        except Exception as e:
            print(f"Error: {e}")
            return f"Error: {e}"
    
    responses = await asyncio.gather(*tasks)
    if errors:
        responses += errors
        return responses
    return responses

async def send_command(url, data, headers):
    async with ClientSession() as session:
        async with session.put(url, data=data, headers=headers) as response:
            return await response.text()

async def get_state_i(drone):
    '''Get the current state of a drone'''
    url = f"http://127.0.0.1:8000/api/vehicle/{drone}/llm/state"
    for i in range(10):
        try:
            async with ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            print(f"Error: {e}, retrying...")
            await asyncio.sleep(1)
    raise DroneStateError(f"Failed to get state of drone {drone}, are you sure it exists?")

async def get_state(drones):
    '''Get the current state of the drones'''
    responses = ""
    for drone in drones:
        for i in range(10):
            try:
                url = f"http://127.0.0.1:8000/api/vehicle/{drone}/llm/state"
                async with ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            responses += await response.text() + "\n"
                            break
            except Exception as e:
                print(f"Error: {e}, retrying...")
                await asyncio.sleep(1)
        else:
            raise DroneStateError(f"Failed to get state of drone {drone}, are you sure it exists?")
    return responses


async def move(drone, distance, direction):
    # Get the current state
    try:
        state = await get_state_i(drone)
    except DroneStateError as e:
        return f"Failed to get state of drone {drone}, are you sure it exists?"
    
    # remove decimals from distance and direction
    distance = int(distance)
    direction = int(direction)

    # Extract the current lat and lon and heading
    current_lat = state['position_geo'][0]
    current_lon = state['position_geo'][1]
    current_heading = state['attitude'][0] * 180 / math.pi

    new_direction = (current_heading + direction) % 360

    # Calculate the new coordinates using the known distance and direction
    new_coords = geodesic(meters=distance).destination((current_lat, current_lon), new_direction)
    new_lat, new_lon = new_coords.latitude, new_coords.longitude

    return new_lat, new_lon

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
        try:
            results = json.loads(results_list[0])
            full_result += f"{results.get('command')}, {results.get('success')}, {results.get('message')}\n"
        except Exception as e:
            results = results_list
            full_result += f"{results}\n"
        print(results)
        
    return full_result

async def arm_drones(drone):
    return_string = ""
    instr_list = "start_mission(patrol), wait(10), pause_mission()"
    instructions_list = parse_instructions(instr_list)
    response = await execute_instructions(drone, instructions_list)
    return_string += f"{response}\n"
    return return_string

# a function that makes both drones come together and fly in half a circle around each other
async def dance(drones):
    if not isinstance(drones, list):
        drones_list = drones.split(',')
        drones = [int(drone) for drone in drones_list]

    # Get the current state of the drones
    state_drone_3 = await get_state_i(drones[0])
    state_drone_4 = await get_state_i(drones[1])
    
    # Check if the states are valid
    if isinstance(state_drone_3, str) or isinstance(state_drone_4, str):
        print(state_drone_3)
        print(state_drone_4)
        return
    
    # Extract the current lat and lon
    current_lat_3 = state_drone_3['position_geo'][0]
    current_lon_3 = state_drone_3['position_geo'][1]
    current_lat_4 = state_drone_4['position_geo'][0]
    current_lon_4 = state_drone_4['position_geo'][1]
    
    # Calculate the middle point (bottom point)
    middle_lat = (current_lat_3 + current_lat_4) / 2
    middle_lon = (current_lon_3 + current_lon_4) / 2
    
    # Move both drones to the middle point
    await run_drone([drones[0]], "move_to", f"{middle_lat}, {middle_lon}")
    await run_drone([drones[1]], "move_to", f"{middle_lat}, {middle_lon}")
    
    # Determine the radius of the circle (half the distance between the drones)
    radius = geodesic((current_lat_3, current_lon_3), (current_lat_4, current_lon_4)).meters / 2

    # Move the drones in a semi-circle path
    for angle in range(0, 181, 10):  # step of 10 degrees
        # Calculate the new coordinates for drone 3 (left)
        new_coords_3 = geodesic(meters=radius).destination((middle_lat, middle_lon), angle)
        new_lat_3, new_lon_3 = new_coords_3.latitude, new_coords_3.longitude
        await run_drone([drones[0]], "move_to", f"{new_lat_3}, {new_lon_3}")
        
        # Calculate the new coordinates for drone 4 (right half )
        new_coords_4 = geodesic(meters=radius).destination((middle_lat, middle_lon), 180 + angle)
        new_lat_4, new_lon_4 = new_coords_4.latitude, new_coords_4.longitude
        await run_drone([drones[1]], "move_to", f"{new_lat_4}, {new_lon_4}")
    
    print("Finished dancing")

        

async def fly_parallel(degrees, drones):
    if not isinstance(drones, list):
        drones_list = drones.split(',')
        drones = [int(drone) for drone in drones_list]

    # Get the current state of the drones
    state_drone_3 = await get_state_i(drones[0])
    state_drone_4 = await get_state_i(drones[1])
    
    # Check if the states are valid
    if isinstance(state_drone_3, str) or isinstance(state_drone_4, str):
        print(state_drone_3)
        print(state_drone_4)
        return
    
    # Extract the current lat and lon
    current_lat_3 = state_drone_3['position_geo'][0]
    current_lon_3 = state_drone_3['position_geo'][1]
    current_lat_4 = state_drone_4['position_geo'][0]
    current_lon_4 = state_drone_4['position_geo'][1]

    # Move both drones to a common point
    middle_lat = (current_lat_3 + current_lat_4) / 2
    middle_lon = (current_lon_3 + current_lon_4) / 2

    await asyncio.gather(
        run_drone([drones[0]], "move_to", f"{middle_lat}, {middle_lon}"),
        run_drone([drones[1]], "move_to", f"{middle_lat}, {middle_lon}")
    )


    # rotate both drones to face the same direction
    await asyncio.gather(
        run_drone([drones[0]], "rotate_to", f"{degrees}, 0"),
        run_drone([drones[1]], "rotate_to", f"{degrees}, 0")
    )

    # Move drone 3 10 meters to the left and drone 4 10 meters to the right
    await asyncio.gather(
        run_drone([drones[0]], "move", "10, 270"),
        run_drone([drones[1]], "move", "10, 90")
    )

    # rotate both drones to face the same direction
    await asyncio.gather(
        run_drone([drones[0]], "rotate_to", f"{degrees}, 0"),
        run_drone([drones[1]], "rotate_to", f"{degrees}, 0")
    )

    # Fly both drones forward for 50 meters
    await asyncio.gather(
        run_drone([drones[0]], "move", "50, 0"),
        run_drone([drones[1]], "move", "50, 0")
    )

    print("Finished flying parallel")


async def duet(drones):
    await fly_parallel(0, drones)
    await dance(drones)
    await fly_parallel(180, drones)
    await dance(drones)

async def parallel_square(drones):
    await fly_parallel(0, drones)
    await fly_parallel(90, drones)
    await fly_parallel(180, drones)
    await fly_parallel(270, drones)

async def save_coords_to_file(name, lat, lon, alt, waypoints_dir="waypoints", waypoints_file="temp_file.json"):
    data = {name.lower(): [lat, lon, alt]}
    waypoints_dir = os.path.join(waypoints_dir)
    if not os.path.exists(waypoints_dir):
        os.makedirs(waypoints_dir)

    waypoints_file = os.path.join(waypoints_dir, waypoints_file)
    try:
        if not os.path.isfile(waypoints_file):
            with open(waypoints_file, "w") as f:
                json.dump([data], f)
            return f"Saved coordinates: {lat}, {lon}, {alt} as {name}"
        else:
            with open(waypoints_file, "r+") as f:
                feeds = json.load(f)
                # Check if name already exists in data
                if not any(name.lower() in d for d in feeds):
                    feeds.append(data)
                    f.seek(0)
                    json.dump(feeds, f)
                    return f"Saved coordinates: {lat}, {lon}, {alt} as {name}"
                # else overwrite the existing name
                else:
                    for d in feeds:
                        if name.lower() in d:
                            d[name.lower()] = [lat, lon, alt]
                    f.seek(0)
                    json.dump(feeds, f)
                    return f"Overwritten coordinates for {name} to: {lat}, {lon}, {alt}"
    except Exception as e:
        return f"Error saving coordinates: {str(e)}"

async def save_drone_coords(drone, name):
    try:
        # Get the current state of the drone
        state_drone = await get_state_i(drone)
        current_lat = state_drone['position_geo'][0]
        current_lon = state_drone['position_geo'][1]
        current_alt = state_drone['position_geo'][2]
    except Exception as e:
        return f"Error getting drone state: {str(e)}"

    return await save_coords_to_file(name, current_lat, current_lon, current_alt)

async def save_coords(parameters):
    # save the drone coords to a name in the waypoints json
    if isinstance(parameters, str):
        coords_list = parameters.split(',')
    else:
        coords_list = parameters

    if len(coords_list) < 3:
        return "Invalid parameters, need at least 3 parameters, name, lat, lon and alt (optional)"
    name = coords_list[0]
    lat = coords_list[1]
    lon = coords_list[2]
    if len(coords_list) == 4:
        alt = coords_list[3]
    else:
        alt = 10

    return await save_coords_to_file(name, lat, lon, alt)

async def move_to_saved(drone, name):
    # move the drone to a name from the waypoints json
    waypoints_file = os.path.join("waypoints", "temp_file.json")
    try:
        with open(waypoints_file, "r") as f:
            waypoints = json.load(f)
        if any(name.lower() in d for d in waypoints):
            for d in waypoints:
                if name.lower() in d:
                    lat, lon, alt = d[name.lower()]
                    await run_drone([drone], "move_to", f"{lat}, {lon}")
                    return f"Moved drone {drone} to {name}"
        else:
            return f"Waypoint {name} not found"
    except Exception as e:
        return f"Error moving drone: {str(e)}"


# async def main():
#     drone = [3]
#     instruction = "save_coords"
#     parameters = "test2, 50.0882423, 24.3732562, -4.634688745580661"
#     response = await run_drone(drone, instruction, parameters)
#     print(response)
#     return

# if __name__ == "__main__":
#     asyncio.run(main())
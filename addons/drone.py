import json
import asyncio
import math
from geopy.distance import geodesic
from aiohttp import ClientSession

description = "Control drones, move(distance(meter), direction(degrees)) example: move(5, 20 (degrees based on current heading)), move_to(lat, long), set_pause_on_detection(True/False), set_follow_on_detection(True/False), start_mission(mission_name), return_home(), resume_mission()), pause_mission(), take_off(meters), execute_instructions(instructions_list) example: execute_instructions([move(10,0), rotate_by(45) move(20,0)]), rotate_by(heading, speed), rotate_to(heading, speed), rotate_gimbal_to(angle), get_state(), look_at(lat, long), square(), duet(), move_to_see(lat, lon, alt), follow_object(object_id), reset_objects()"
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
            elif instruction == "duet":
                await duet()
                return "Finished duet"
            elif instruction == "square":
                await square()
                return "Finished square"
            elif instruction == "move_to_see":
                if isinstance(parameters, str):
                    parameters_list = parameters.split(',')
                else:
                    parameters_list = parameters
                if len(parameters_list) != 3:
                    return "Invalid parameters, need 3 parameters, lat, lon and alt"
                lat = float(parameters_list[0])
                lon = float(parameters_list[1])
                alt = float(parameters_list[2].strip())
                data = f"move_to_see({lat}, {lon}, {alt})"
            elif instruction == "follow_object":
                data = f"follow_object({parameters})"
            elif instruction == "reset_objects":
                data = "reset_objects()"
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
    for i in range(10):  # retry up to 10 times
        try:
            async with ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            print(f"Error: {e}, retrying...")
            await asyncio.sleep(1)  # wait for 1 second before retrying
    return "Failed to get state"

async def get_state(drones):
    '''Get the current state of the drones'''
    responses = ""
    for drone in drones:
        for i in range(10):  # retry up to 10 times
            try:
                url = f"http://127.0.0.1:8000/api/vehicle/{drone}/llm/state"
                async with ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            responses += await response.text() + "\n"
                            break  # break the retry loop if successful
            except Exception as e:
                print(f"Error: {e}, retrying...")
                await asyncio.sleep(1)  # wait for 1 second before retrying
        else:  # this else block is executed if the for loop completed normally (no break statement was encountered)
            responses += f"Error: Failed to get state for drone {drone}\n"
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



# a function that makes both drones come together and fly in half a circle around each other
async def dance():
    # Get the current state of the drones
    state_drone_3 = await get_state_i(3)
    state_drone_4 = await get_state_i(4)
    
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
    await run_drone([3], "move_to", f"{middle_lat}, {middle_lon}")
    await run_drone([4], "move_to", f"{middle_lat}, {middle_lon}")
    
    # Determine the radius of the circle (half the distance between the drones)
    radius = geodesic((current_lat_3, current_lon_3), (current_lat_4, current_lon_4)).meters / 2

    # Move the drones in a semi-circle path
    for angle in range(0, 181, 10):  # step of 10 degrees
        # Calculate the new coordinates for drone 3 (left)
        new_coords_3 = geodesic(meters=radius).destination((middle_lat, middle_lon), angle)
        new_lat_3, new_lon_3 = new_coords_3.latitude, new_coords_3.longitude
        await run_drone([3], "move_to", f"{new_lat_3}, {new_lon_3}")
        
        # Calculate the new coordinates for drone 4 (right half )
        new_coords_4 = geodesic(meters=radius).destination((middle_lat, middle_lon), 180 + angle)
        new_lat_4, new_lon_4 = new_coords_4.latitude, new_coords_4.longitude
        await run_drone([4], "move_to", f"{new_lat_4}, {new_lon_4}")
    
    print("Finished dancing")

        

async def fly_paralell(degrees):
    # Get the current state of the drones
    state_drone_3 = await get_state_i(3)
    state_drone_4 = await get_state_i(4)
    
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
        run_drone([3], "move_to", f"{middle_lat}, {middle_lon}"),
        run_drone([4], "move_to", f"{middle_lat}, {middle_lon}")
    )


    # rotate both drones to face the same direction
    await asyncio.gather(
        run_drone([3], "rotate_to", f"{degrees}, 0"),
        run_drone([4], "rotate_to", f"{degrees}, 0")
    )

    # Move drone 3 10 meters to the left and drone 4 10 meters to the right
    await asyncio.gather(
        run_drone([3], "move", "10, 270"),
        run_drone([4], "move", "10, 90")
    )

    # rotate both drones to face the same direction
    await asyncio.gather(
        run_drone([3], "rotate_to", f"{degrees}, 0"),
        run_drone([4], "rotate_to", f"{degrees}, 0")
    )

    # Fly both drones forward for 50 meters
    await asyncio.gather(
        run_drone([3], "move", "50, 0"),
        run_drone([4], "move", "50, 0")
    )

    print("Finished flying parallel")


async def duet():
    await fly_paralell(0)
    await dance()
    await fly_paralell(180)
    await dance()

async def square():
    await fly_paralell(0)
    await fly_paralell(90)
    await fly_paralell(180)
    await fly_paralell(270)

# async def main():
#     # # get drone 3 state
#     # drone = 3
#     # instr_list = "move(10, 0), rotate_by(10), move(10, 0), rotate_by(10),move(10, 0), rotate_by(10),move(10, 0), rotate_by(10),move(10, 0), rotate_by(10),"
#     # instructions_list = parse_instructions(instr_list)
#     # response = await execute_instructions(drone, instructions_list)
#     # print(response)
#     await fly_paralell(0)
#     await dance()
#     await fly_paralell(180)
#     await dance()

# # Python 3.7+
# if __name__ == "__main__":
#     asyncio.run(main())
import requests

description = "Interact with the home assistant API"
parameters = {
    "type": "object",
    "properties": {
        "room": {
            "type": "string",
            "description": "The room where to control the lights or set/get the temperature, use the room names from the home info",
        },
        "action": {
            "type": "string",
            "description": "turn_off_light, turn_on_light, set_temperature, get_temperature, get_home_info",
        },
        "temperature": {
            "type": "number",
            "description": "The temperature to set in the room, only required for set_temperature action",
        },
    },
    "required": ["room", "action"],
}

from utils import config
API_URL = config.HOUSE_API_URL + "api"
SECRET_KEY = config.HOUSE_API_KEY

def interact_with_home_assistant(room, action, temperature=None):
    if action == 'set_temperature':
        if temperature is None:
            raise ValueError("Temperature is required for set_temperature action")

    try:
        if action == 'set_temperature':
            response = requests.get(
                API_URL,
                params={
                    'key': SECRET_KEY,
                    'action': action,
                    'args': f'{room},{temperature}'
                }
            )
        else:
            response = requests.get(
                API_URL,
                params={
                    'key': SECRET_KEY,
                    'action': action,
                    'args': room
                }
            )
    except requests.exceptions.ConnectionError:
        return f'Failed to connect to the API at {API_URL}'

    if response.status_code == 200:
        print(f'{response.text}')
        return f'Successfully executed {action} in {room}'
    else:
        print(f'{response.text}')
        return f'Failed to execute {action} in {room}. Status code: {response.status_code}'

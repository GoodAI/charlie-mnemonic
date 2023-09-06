import requests
import config

description = "Get the current weather in a given location"

parameters = {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "The city,  e.g. Brussels",
        },
        "unit": {"type": "string", "enum": ["standard", "metric", "imperial"]},
    },
    "required": ["location"],
}

def get_current_weather(location, unit="metric"):
    openweather_api_key = config.OPENWEATHER_API_KEY
    url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&units={unit}&appid={openweather_api_key}"
    response = requests.get(url).text
    return response

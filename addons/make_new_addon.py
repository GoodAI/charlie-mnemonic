description = "Used to create a new addon (not for other code!), after receiving the code, you will create the file in the addons directory and paste the code in it after using this addon"

parameters = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "The description of the addon",
        },
        "details": {"type": "string", "details": "The details of the addon"},
    },
    "required": ["description"],
}

def make_new_addon(description, details = None):
    prompt = '''
    You are tasked with creating an addon/function that can be used by yourself. You will be given a name and description for your plugin. You will return code in a codebox, and a short explanation.
    The filename should be the same as the function name!
    Make sure everything works, revisions might be needed, but try to make it work the first time. Only use APIs that are free to use unless the user specifies otherwise. Add basic error handling.
    After receiving the code, you will create the file in the addons directory and paste the code in it after using this addon
    use the same format as the example, The parameters are important, even if empty, declare the type! described as a JSON Schema object. Do not forget the required variables. Here is an example of a plugin:
    
    """"
    import requests
    import config

    description = "Get the current weather in a given location" #required!!!

    parameters = { #required!!!
        "type": "object", #required!!!
        "properties": { #required but can be empty
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA",
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
    '''
    result = prompt + f'The user wants an addon with description: {description} and details: {details}'
    return result
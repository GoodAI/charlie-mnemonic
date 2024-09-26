import os
import config
from llmcalls import get_responder
from utils import convert_username, SettingsManager
import urllib.parse

description = "Get the descriptions of one or more images using your vision capabilities, only use this for PNG, JPEG, GIF and WEBP images."
parameters = {
    "type": "object",
    "properties": {
        "image_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "image_paths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "description": "The paths to the image files. Example: ['data/image1.jpg', 'data/image2.jpg']",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to provide context for the image descriptions",
                    },
                },
                "required": ["image_paths", "prompt"],
            },
        },
    },
    "required": ["image_requests"],
}


async def get_image_descriptions(image_requests, username=None):
    settings = await SettingsManager.load_settings("users", username)
    active_model = settings.get("active_model", {}).get("active_model", "gpt-4")

    api_key = (
        config.api_keys["openai"]
        if active_model.startswith("gpt")
        else config.api_keys["anthropic"]
    )
    responder = get_responder(api_key, active_model)

    results = []
    for request in image_requests:
        image_paths = request["image_paths"]
        prompt = request["prompt"]
        username = convert_username(username)
        charlie_mnemonic_user_dir = os.path.join(os.getcwd(), "users")
        full_path = os.path.join(charlie_mnemonic_user_dir, username, "data")

        # detect if we are in a docker container or not
        if os.path.exists("/.dockerenv"):
            full_image_paths = [
                os.path.join(
                    "/app",
                    "users",
                    username,
                    "data",
                    urllib.parse.unquote(os.path.basename(image_path)),
                )
                for image_path in image_paths
            ]
        else:
            full_image_paths = [
                os.path.join(
                    full_path, urllib.parse.unquote(os.path.basename(image_path))
                )
                for image_path in image_paths
            ]

        try:
            resp = await responder.get_image_description(
                image_paths=full_image_paths, prompt=prompt, username=username
            )
            results.append({"request": request, "description": resp})
        except Exception as e:
            results.append({"request": request, "error": str(e)})

    return results

import base64
import os
import openai
import config
from llmcalls import OpenAIResponser

description = "Get the descriptions of one or more images using the OpenAI Vision API, only use this for PNG, JPEG, and GIF and WEBP images."
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
    openai.api_key = config.api_keys["openai"]
    results = []
    for request in image_requests:
        image_paths = request["image_paths"]
        prompt = request["prompt"]
        username = username

        charlie_mnemonic_user_dir = os.path.join(os.getcwd(), "users")
        full_path = os.path.join(charlie_mnemonic_user_dir, username, "data")

        # detect if we are in a docker container or not
        if os.path.exists("/.dockerenv"):
            full_image_paths = [
                os.path.join(
                    "/app", "users", username, "data", os.path.basename(image_path)
                )
                for image_path in image_paths
            ]
        else:
            full_image_paths = [
                os.path.join(full_path, os.path.basename(image_path))
                for image_path in image_paths
            ]

        try:
            openai_response = OpenAIResponser(config.api_keys["openai"])
            resp = await openai_response.get_image_description(
                image_paths=full_image_paths, prompt=prompt
            )
            results.append({"request": request, "description": resp})
        except Exception as e:
            results.append({"request": request, "error": str(e)})

    return results

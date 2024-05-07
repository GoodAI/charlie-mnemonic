import base64
import os
import openai
import config
from llmcalls import OpenAIResponser

description = "Get the description of one or more images using the OpenAI Vision API"
parameters = {
    "type": "object",
    "properties": {
        "image_paths": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "The paths to the image files",
        },
        "prompt": {
            "type": "string",
            "description": "The prompt to provide context for the image descriptions",
        },
    },
    "required": ["image_paths", "prompt"],
}


async def get_image_descriptions(image_paths, prompt, username=None):
    openai.api_key = config.api_keys["openai"]
    descriptions = []

    for image_path in image_paths:
        full_image_path = "/" + os.path.join("app", "users", username, image_path)
        # remove the leading slash if there is more than one (gpt is sometimes adding an extra slash)
        full_image_path = (
            full_image_path[1:] if full_image_path.startswith("//") else full_image_path
        )
        print(f"Getting description for image at path: {full_image_path}")

        try:
            openai_response = OpenAIResponser(config.api_keys["openai"])
            resp = await openai_response.get_image_description(
                image_path=full_image_path, prompt=prompt
            )
            descriptions.append(resp)
        except Exception as e:
            descriptions.append({"error": str(e), "image_path": full_image_path})

    return descriptions

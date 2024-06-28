import openai
import config
import os
import requests
from utils import convert_username

description = "Generate an image based on a text prompt and save it to disk"
parameters = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "The text prompt to generate an image from",
        },
        "size": {
            "type": "string",
            "enum": ["1024x1024", "1024x1792", "1792x1024"],
            "default": "1024x1024",
            "description": "The size of the generated image",
        },
        "quality": {
            "type": "string",
            "enum": ["standard", "hd"],
            "default": "standard",
            "description": "The quality of the generated image (only applicable for DALL·E 3)",
        },
    },
    "required": ["prompt"],
}


def generate_image(prompt, size="1024x1024", quality="standard", n=1, username=None):
    openai.api_key = config.api_keys["openai"]
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
        )
    except Exception as e:
        return str(e)

    username = convert_username(username)
    # Get the user's data directory path
    charlie_mnemonic_user_dir = os.path.join(os.getcwd(), "users")
    user_data_dir = os.path.join(charlie_mnemonic_user_dir, username, "data")
    os.makedirs(user_data_dir, exist_ok=True)

    image_paths = []
    volume_paths = []
    random_string = os.urandom(8).hex()
    for i, data in enumerate(response.data):
        image_url = data.url
        image_filename = f"generated_image_{random_string}_{i+1}.png"
        image_path = os.path.join(user_data_dir, image_filename)
        volume_path = os.path.join("data", image_filename)

        # Download the image and save it to disk
        image_data = requests.get(image_url).content
        with open(image_path, "wb") as file:
            file.write(image_data)

        image_paths.append(image_path)
        volume_paths.append(volume_path)
    return {"image_paths": volume_paths}

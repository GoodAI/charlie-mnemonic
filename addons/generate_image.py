import openai
import config
import os
import requests
from utils import convert_username

description = "Generate multiple images based on text prompts and save them to disk"
parameters = {
    "type": "object",
    "properties": {
        "prompts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "An array of text prompts to generate images from",
        },
        "size": {
            "type": "string",
            "enum": ["1024x1024", "1024x1792", "1792x1024"],
            "default": "1024x1024",
            "description": "The size of the generated images",
        },
        "quality": {
            "type": "string",
            "enum": ["standard", "hd"],
            "default": "standard",
            "description": "The quality of the generated images (only applicable for DALL·E 3)",
        },
    },
    "required": ["prompts"],
}


def generate_image(prompts, size="1024x1024", quality="standard", username=None):
    openai.api_key = config.api_keys["openai"]

    username = convert_username(username)
    charlie_mnemonic_user_dir = os.path.join(os.getcwd(), "users")
    user_data_dir = os.path.join(charlie_mnemonic_user_dir, username, "data")
    os.makedirs(user_data_dir, exist_ok=True)

    image_paths = []
    volume_paths = []
    random_string = os.urandom(3).hex()

    for index, prompt in enumerate(prompts):
        try:
            response = openai.images.generate(
                model="dall-e-3", prompt=prompt, size=size, quality=quality, n=1
            )
        except Exception as e:
            return str(e)

        for i, data in enumerate(response.data):
            image_url = data.url
            image_filename = f"generated_image_{random_string}_{index+1}_{i+1}.png"
            image_path = os.path.join(user_data_dir, image_filename)
            volume_path = os.path.join("data", image_filename)

            # Download the image and save it to disk
            image_data = requests.get(image_url).content
            with open(image_path, "wb") as file:
                file.write(image_data)

            image_paths.append(image_path)
            volume_paths.append(volume_path)

    return {"image_paths": volume_paths}

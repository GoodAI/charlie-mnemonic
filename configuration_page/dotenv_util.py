import os.path
from typing import Dict


def update_dotenv_file(path: str, updates: Dict[str, str]) -> None:
    print(f"Entering update_dotenv_file with path: {path} and updates: {updates}")
    env_contents = ""
    if os.path.exists(path):
        with open(path, "r") as f:
            env_contents = f.read()
    else:
        print(f"Creating new .env file at {path}")

    updated_contents = update_dotenv_contents(env_contents, updates)

    with open(path, "w") as f:
        f.write(updated_contents)


def update_dotenv_contents(env_contents: str, updates: Dict[str, str]) -> str:
    updated_lines = []
    found_keys = set()

    lines = env_contents.splitlines()
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                updated_lines.append(f"{key}={updates[key]}")
                found_keys.add(key)
                continue
        updated_lines.append(line)

    # Add any new keys that weren't found in the file
    new_keys = set(updates.keys()) - found_keys
    for key in new_keys:
        updated_lines.append(f"{key}={updates[key]}")

    result = "\n".join(updated_lines)
    print(f"Exiting update_dotenv_contents with result:\n{result}")
    return result

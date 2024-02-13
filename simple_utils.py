"""
Simple utils with no big dependencies. Cannot be in utils due to circular imports.
Ideally move here only things that don't require any local dependencies.
"""
import os
from pathlib import Path

from unidecode import unidecode


def get_root(path_to_join: str = None) -> Path:
    if not path_to_join:
        return Path(__file__).parent
    return Path(os.path.join(Path(__file__).parent, path_to_join))


def convert_name(name):
    # Convert non-ASCII characters to ASCII
    name = unidecode(name)
    # replace spaces with underscores
    name = name.replace(" ", "_")
    name = name.replace("@", "_")
    name = name.replace(".", "_")
    # lowercase the name
    return name.lower()

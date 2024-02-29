"""
Simple utils with no big dependencies. Cannot be in utils due to circular imports.
Ideally move here only things that don't require any local dependencies.
"""

import os
from pathlib import Path
import re

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


def parse_memory_cat_string(s):
    # Remove characters not allowed (rule 3)
    s = re.sub(r"[^a-zA-Z0-9_\-]", "", s)

    # Ensure it starts and ends with an alphanumeric character (rule 2)
    s = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", s)

    # Limit the length to 63 characters (rule 1)
    s = s[:63]

    return s

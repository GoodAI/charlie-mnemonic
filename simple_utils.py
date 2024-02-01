"""
Simple utils with no big dependencies. Cannot be in utils due to circular imports.
Ideally move here only things that don't require any local dependencies.
"""
import os
from pathlib import Path


def get_root(path_to_join: str = None) -> Path:
    if not path_to_join:
        return Path(__file__).parent
    return Path(os.path.join(Path(__file__).parent, path_to_join))


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

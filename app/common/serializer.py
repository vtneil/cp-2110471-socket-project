import pickle
from typing import Any


def serialize(obj) -> bytes:
    return pickle.dumps(obj)


def deserialize(stream: bytes) -> Any:
    return pickle.loads(stream)

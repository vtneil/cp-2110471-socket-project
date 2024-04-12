import pickle


def serialize(obj):
    return pickle.dumps(obj)


def deserialize(stream: bytes):
    return pickle.loads(stream)

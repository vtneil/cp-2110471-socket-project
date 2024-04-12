from src.common import *


if __name__ == '__main__':
    msg = Message(('gr1', 'vt'), ('gr1', 'tv'), 'str', b'1234')
    out = serialize(msg)
    m = deserialize(out)
    print(type(m))

from .serializer import serialize, deserialize
from .user import User
import dataclasses


class Response:
    OK = 200
    WARN = 400
    ERROR = 500


class MessageType:
    class INSTRUCTION:
        IDENTIFY = 1000
        RESPONSE = 1001

        class CLIENT:
            LIST = 2000

        class GROUP:
            LIST_GROUPS = 3000
            LIST_CLIENTS = 3001
            JOIN = 3002
            LEAVE = 3003

    class DATA:
        PLAIN_TEXT = 100
        IMAGE = 101
        VIDEO = 102
        VOICE = 103
        FILE = 104

    @staticmethod
    def is_instruction(code) -> bool:
        return code >= 1000

    @staticmethod
    def is_data(code) -> bool:
        return not MessageType.is_instruction(code)


@dataclasses.dataclass(init=True, repr=True, order=True)
class Message:
    src: User | None
    dst: User | None
    message_type: MessageType
    _data: bytes

    @property
    def data(self):
        return deserialize(self._data)

    @data.setter
    def data(self, v):
        self._data = serialize(v)


def new_message(src: User | None, dst: User | None, message_type: MessageType, data):
    m = Message(
        src=src,
        dst=dst,
        message_type=message_type,
        _data=serialize(data)
    )
    return m

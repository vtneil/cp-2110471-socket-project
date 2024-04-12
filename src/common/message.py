import dataclasses


@dataclasses.dataclass
class Message:
    src: tuple[str, str]  # (Group, Client)
    dst: tuple[str, str]  # (Group, Client)
    message_type: str
    message: bytes

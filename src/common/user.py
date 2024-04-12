import dataclasses
import socket


@dataclasses.dataclass(init=True, repr=True, order=True, frozen=True)
class User:
    username: str | None
    group: str | None
    address: tuple[str, int] | None  # Socket: (Host, Port)
    sock: socket.socket | None


def new_user(username: str | None,
             group: str | None = None,
             address: tuple[str, int] | None = None,
             sock: socket.socket | None = None):
    return User(username=username, group=group, address=address, sock=sock)

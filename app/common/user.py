import dataclasses
import socket


@dataclasses.dataclass(init=True, repr=True, order=True)
class User:
    username: str | None
    group: str | None
    address: tuple[str, int] | None  # Socket: (Host, Port)
    sock_master: socket.socket | None
    sock_slaves: list[socket.socket] | None


def new_user(username: str | None,
             group: str | None = None,
             address: tuple[str, int] | None = None,
             sock_master: socket.socket | None = None,
             sock_slaves: list[socket.socket] | None = None):
    return User(username=username,
                group=group,
                address=address,
                sock_master=sock_master,
                sock_slaves=sock_slaves)

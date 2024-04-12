from typing import Literal
import socket
from .. import serialize, deserialize


def new_socket(socket_type: Literal['tcp', 'udp']) -> socket.socket:
    if socket_type == 'tcp':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    return sock


def send_to_sock(sock: socket.socket, data):
    sock.sendall(serialize(data))


def receive_from_sock(sock: socket.socket, buffer_size: int = 1024):
    return deserialize(sock.recv(buffer_size))


def get_internet_ip() -> str:
    s = new_socket('udp')
    s.connect(('8.8.8.8', 80))
    o = s.getsockname()[0]
    s.close()
    return o

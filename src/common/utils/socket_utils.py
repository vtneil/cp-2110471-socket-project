from typing import Literal
import socket


def new_socket(socket_type: Literal['tcp', 'udp']) -> socket.socket:
    if socket_type == 'tcp':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sock


def get_internet_ip() -> str:
    s = new_socket('udp')
    s.connect(("8.8.8.8", 80))
    o = s.getsockname()[0]
    s.close()
    return o

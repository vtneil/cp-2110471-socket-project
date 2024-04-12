from typing import Literal
import socket


def new_socket(socket_type: Literal['tcp', 'udp']) -> socket.socket:
    if socket_type == 'tcp':
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

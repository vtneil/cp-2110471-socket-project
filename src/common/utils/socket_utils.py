from typing import Literal, Any
import socket
from .. import serialize, deserialize


def new_socket(socket_type: Literal['tcp', 'udp']) -> socket.socket:
    if socket_type == 'tcp':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    return sock


def tcp_sock_send(sock: socket.socket, data: Any):
    sock.sendall(serialize(data))


def udp_sock_send(sock: socket.socket, address: tuple[str, int], data: Any):
    sock.sendto(serialize(data), address)


def tcp_sock_recv(sock: socket.socket, buffer_size: int = 1024, timeout: float | None = 2.) -> Any:
    """
    Raises socket.timeout if a timeout occurs
    """

    # return deserialize(sock.recv(buffer_size))

    chunks = []
    prev_timeout = sock.timeout
    sock.settimeout(timeout)

    try:
        while True:
            data = sock.recv(buffer_size)
            chunks.append(data)

            if len(data) < buffer_size:
                break
    except Exception:
        raise
    finally:
        sock.settimeout(prev_timeout)

    all_data = b''.join(chunks)

    return deserialize(all_data)


def udp_sock_recv(sock: socket.socket, buffer_size: int = 1024, timeout: float | None = 2.) -> tuple[Any, Any]:
    chunks = []
    prev_timeout = sock.timeout
    address = None
    sock.settimeout(timeout)

    try:
        while True:
            data, addr = sock.recvfrom(buffer_size)

            if address is None:
                address = addr
            elif address != addr:
                continue

            chunks.append(data)

            if len(data) < buffer_size:
                break
    except socket.timeout:
        pass
    finally:
        sock.settimeout(prev_timeout)

    all_data = b''.join(chunks)
    return deserialize(all_data), address


def get_internet_ip() -> str:
    s = new_socket('udp')
    s.connect(('8.8.8.8', 80))
    o = s.getsockname()[0]
    s.close()
    return o

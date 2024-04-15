from typing import Any

from .. import *
from abc import abstractmethod
import socket
import time


class Client:
    def __init__(self, name: str, host: str, port: int, sock: socket.socket):
        self._sock = sock
        self.__name = name
        self.__address = (host, port)

    @abstractmethod
    def send(self, data: Any):
        pass

    @abstractmethod
    def receive(self, buffer_size: int):
        pass

    def transaction(self, data: Any, buffer_size: int = 16384):
        self.send(data)
        return self.receive(buffer_size)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def address(self) -> tuple[str, int]:
        return self.__address

    def close(self):
        self._sock.close()

    def __del__(self):
        self.close()


class TcpClient(Client):
    def __init__(self, name: str, remote_host: str, remote_port: int, retry: float = 1.0):
        super().__init__(name, remote_host, remote_port, new_socket('tcp'))

        while True:
            try:
                self._sock.connect(self.address)
                break
            except socket.error:
                logger.error(f'Error connecting to server, retrying in {retry} s...')
                time.sleep(retry)

    def send(self, data: Any):
        try:
            tcp_sock_send(self._sock, data)
        except socket.timeout:
            pass
        except socket.error as e:
            logger.exception(f'Error sending data: {e}')
            raise

    def receive(self, buffer_size: int = 16384):
        try:
            return tcp_sock_recv(self._sock, buffer_size)
        except socket.timeout:
            pass
        except socket.error as e:
            logger.exception(f'Error receiving data: {e}')
            raise


class UdpClient(Client):
    def __init__(self, name: str, remote_host: str, remote_port: int):
        super().__init__(name, remote_host, remote_port, new_socket('udp'))

    def send(self, data: Any):
        try:
            udp_sock_send(self._sock, self.address, data)
        except socket.timeout:
            pass
        except socket.error as e:
            logger.exception(f'Error sending data: {e}')
            raise

    def receive(self, buffer_size: int = 16384):
        try:
            return udp_sock_recvfrom(self._sock, buffer_size)[0]
        except socket.timeout:
            pass
        except socket.error as e:
            logger.exception(f'Error receiving data: {e}')
            raise

from ..socket_utils import *
import logging
from abc import abstractmethod


class Client:
    def __init__(self, name: str, host: str, port: int, sock: socket.socket):
        self._sock = sock
        self.__name = name
        self.__address = (host, port)

    @abstractmethod
    def send(self, data):
        pass

    @abstractmethod
    def receive(self, buffer_size):
        pass

    @property
    def name(self) -> str:
        return self.__name

    @property
    def address(self) -> tuple:
        return self.__address

    def close(self):
        self._sock.close()

    def __del__(self):
        self._sock.close()


class TcpClient(Client):
    def __init__(self, name: str, host: str, port: int):
        super().__init__(name, host, port, new_socket('tcp'))
        try:
            self._sock.connect(self.address)
        except socket.error as e:
            logging.error(f'Error connecting to server: {e}')
            raise

    def send(self, data: bytes):
        try:
            self._sock.sendall(data)
        except socket.error as e:
            logging.error(f'Error sending data: {e}')
            raise

    def receive(self, buffer_size: int = 1024) -> bytes:
        try:
            return self._sock.recv(buffer_size)
        except socket.error as e:
            logging.error(f'Error receiving data: {e}')
            raise


class UdpClient(Client):
    def __init__(self, name: str, host: str, port: int):
        super().__init__(name, host, port, new_socket('udp'))

    def send(self, data: bytes):
        try:
            self._sock.sendto(data, self.__address)
        except socket.error as e:
            print(f"Error sending data: {e}")
            raise

    def receive(self, buffer_size: int = 1024) -> bytes:
        try:
            return self._sock.recvfrom(buffer_size)[0]
        except socket.error as e:
            print(f"Error receiving data: {e}")
            raise

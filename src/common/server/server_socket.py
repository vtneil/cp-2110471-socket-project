from ..socket_utils import *
import logging
import threading
from abc import abstractmethod


class Server:
    def __init__(self, host: str, port: int, sock: socket.socket):
        self.__sock = sock
        self.__address = (host, port)
        self.__sock.bind(self.__address)
        self.__sock.listen()

    @abstractmethod
    def start(self):
        pass

    def stop(self):
        self.__sock.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class TcpServer(Server):
    def __init__(self, host: str, port: int):
        super().__init__(host, port, new_socket('tcp'))

    def start(self):
        pass


class UdpServer(Server):
    def __init__(self, host: str, port: int):
        super().__init__(host, port, new_socket('udp'))

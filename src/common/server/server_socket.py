from typing import Callable
from abc import abstractmethod

from .. import *
from .. import logger
import threading
import socket


class Server:
    def __init__(self, host: str, port: int, sock: socket.socket):
        self._sock = sock
        self.__address = (host, port)

    @abstractmethod
    def start(self,
              callback: Callable[[socket.socket, tuple[str, int]], None] | Callable[[bytes, tuple[str, int]], None]):
        pass

    def stop(self):
        self._sock.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    @property
    def address(self) -> tuple:
        return self.__address


class TcpServer(Server):
    def __init__(self, host: str, port: int):
        super().__init__(host, port, new_socket('tcp'))
        self._sock.settimeout(1.)
        logger.info('TCP Server is created.')

    def start(self, callback: Callable[[socket.socket, tuple[str, int]], None]):
        self._sock.bind(self.address)
        self._sock.listen()
        logger.info(f'TCP Server started at {self.address[0]}:{self.address[1]}. Waiting for connections...')
        self.__accept_connections(callback=callback)

    def __accept_connections(self, callback: Callable[[socket.socket, tuple[str, int]], None]):
        try:
            while True:
                try:
                    client_sock, client_addr = self._sock.accept()
                    logger.info(f'Connected with {client_addr}')

                    if callback:
                        threading.Thread(
                            target=callback,
                            args=(client_sock, client_addr),
                            daemon=True
                        ).start()
                except socket.timeout:
                    pass

        except Exception as e:
            logger.exception(f'TCP Server error: {e}')
            raise


class UdpServer(Server):
    def __init__(self, host: str, port: int):
        super().__init__(host, port, new_socket('udp'))
        self._sock.settimeout(1.)

    def start(self, callback: Callable[[bytes, tuple[str, int]], None]):
        self._sock.bind(self.address)
        logger.info(f'UDP Server started at {self.address[0]}:{self.address[1]}. Waiting for connections...')
        self.__receive_data(callback=callback)

    def __receive_data(self, callback: Callable[[bytes, tuple[str, int]], None]):
        try:
            while True:
                try:
                    client_data, client_addr = udp_sock_recvfrom(self._sock, 1024)
                    logger.info(f'Received data from {client_addr}')

                    if callback:
                        threading.Thread(
                            target=callback,
                            args=(client_data, client_addr),
                            daemon=True
                        ).start()
                except socket.timeout:
                    pass
        except Exception as e:
            logger.exception(f'UDP Server error: {e}')
            raise

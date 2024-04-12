import socket
from typing import Callable
from abc import abstractmethod

from .. import *
from .. import logger
import threading


class Server:
    def __init__(self, host: str, port: int, sock: socket.socket):
        self._sock = sock
        self.__address = (host, port)

    @abstractmethod
    def start(self, callback: Callable[[socket.socket, tuple[str, int]], None]):
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
                except TimeoutError:
                    pass

        except Exception as e:
            logger.error(f'Server error: {e}')
            raise


class UdpServer(Server):
    def __init__(self, host: str, port: int):
        super().__init__(host, port, new_socket('udp'))
        raise NotImplementedError('Not implemented yet!')

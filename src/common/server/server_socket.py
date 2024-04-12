from .. import *
from .. import logger
import threading

from abc import abstractmethod


class Server:
    def __init__(self, host: str, port: int, sock: socket.socket):
        self._sock = sock
        self.__address = (host, port)

        self._clients: list = []

    @abstractmethod
    def start(self):
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
        logger.info('TCP Server is created.')

    def start(self):
        self._sock.bind(self.address)
        self._sock.listen()
        logger.info(f'TCP Server started at {self.address[0]}:{self.address[1]}. Waiting for connections...')
        self.__accept_connections()

    def __accept_connections(self):
        try:
            while True:
                client, addr = self._sock.accept()
                self._clients.append((client, addr))

                logger.info(f'Connected with {addr}')
                threading.Thread(target=self.__handle_client, args=(client, addr), daemon=True).start()

        except Exception as e:
            logger.error(f'Server error: {e}')
            raise

    def __handle_client(self, client_socket: socket.socket, client_address: str):
        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                logger.info(f'Received from {client_address}: {deserialize(data)}')
                client_socket.sendall(data)  # Echo
        except socket.error:
            logger.warning('Connection is forcibly reset by the client!')
        finally:
            client_socket.close()
            logger.info(f'Connection closed with {client_address}')


class UdpServer(Server):
    def __init__(self, host: str, port: int):
        super().__init__(host, port, new_socket('udp'))
        raise NotImplementedError('Not implemented yet!')

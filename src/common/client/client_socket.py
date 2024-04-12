import socket
import time

from .. import *
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
    def __init__(self, name: str, remote_host: str, remote_port: int, retry: float = 1.0):
        super().__init__(name, remote_host, remote_port, new_socket('tcp'))

        while True:
            try:
                self._sock.connect(self.address)
                logger.info('Successfully connected to server!')
                break
            except socket.error:
                logger.error(f'Error connecting to server, retrying in {retry} s...')
                time.sleep(retry)

    def send(self, data):
        try:
            send_to_sock(self._sock, data)
        except socket.error as e:
            logger.error(f'Error sending data: {e}')
            raise

    def receive(self, buffer_size: int = 1024):
        try:
            return receive_from_sock(self._sock, buffer_size)
        except socket.error as e:
            logger.error(f'Error receiving data: {e}')
            raise


class UdpClient(Client):
    def __init__(self, name: str, remote_host: str, remote_port: int):
        super().__init__(name, remote_host, remote_port, new_socket('udp'))

    def send(self, data):
        try:
            self._sock.sendto(serialize(data), self.__address)
        except socket.error as e:
            print(f'Error sending data: {e}')
            raise

    def receive(self, buffer_size: int = 1024):
        try:
            return deserialize(self._sock.recvfrom(buffer_size)[0])
        except socket.error as e:
            print(f'Error receiving data: {e}')
            raise

    def broadcast(self):
        sock = new_socket('udp')
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        broadcast_address = '255.255.255.255'
        broadcast_message = serialize((self.name, self.address))
        sock.sendto(broadcast_message, (broadcast_address, 50001))

    def listen_broadcast(self):
        sock = new_socket('udp')
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 50001))

        while True:
            message, addr = sock.recvfrom(1024)
            print('Received message: %s from %s' % (deserialize(message), addr))

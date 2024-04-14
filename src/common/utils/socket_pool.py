import socket
import threading
from contextlib import contextmanager
from .. import *


class SocketPool:
    def __init__(self, socks: list[socket.socket]):
        self.__pool: list[socket.socket | None] = socks.copy()
        self.__lock = threading.Lock()
        self.__available = threading.Semaphore(len(self.__pool))

    @contextmanager
    def get_socket(self) -> socket.socket:
        sock = self.acquire_socket()
        try:
            yield sock
        finally:
            self.release_socket(sock)

    def acquire_socket(self) -> socket.socket:
        self.__available.acquire()
        with self.__lock:
            for i, sock in enumerate(self.__pool):
                if sock:
                    self.__pool[i] = None
                    return sock

    def release_socket(self, sock: socket.socket):
        with self.__lock:
            for i, s in enumerate(self.__pool):
                if s is None:
                    self.__pool[i] = sock
                    break
        self.__available.release()

    @property
    def value(self):
        return self.__available._value

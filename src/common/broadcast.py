import time
from typing import Callable, Any

from . import logger, new_socket, udp_sock_send, udp_sock_recvfrom
from . import MessageProtocol, MessageProtocolCode, new_message_proto
from . import new_user
import socket
import threading


class UdpBroadcast:
    def __init__(self,
                 service_name: str,
                 broadcast_mode: MessageProtocolCode,
                 disc_callback: Callable[[MessageProtocol], None] | None = None,
                 broadcast_address: str = '255.255.255.255',
                 listen_port: int = 50001,
                 broadcast_period: float = 1.0):

        self.__message = new_message_proto(
            src=new_user(username=service_name),
            dst=None,
            message_type=broadcast_mode,
            body=None
        )
        self.__address = broadcast_address
        self.__listen_port = listen_port
        self.__period = broadcast_period

        self.__create_sockets()
        logger.info('Broadcasting sockets has been created!')

        self.__thread_flag = threading.Event()
        self.__broadcast_thread = self.__start_broadcast()
        self.__listener_thread = self.__start_listen(disc_callback)
        logger.info('Started broadcasting and listening!')

    def __create_sockets(self):
        self.__listener = new_socket('udp')
        self.__listener.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__listener.bind(('', self.__listen_port))

        self.__broadcaster = new_socket('udp')
        self.__broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __broadcast_next(self):
        udp_sock_send(self.__broadcaster, (self.__address, self.__listen_port), self.__message)

    def __start_broadcast(self) -> threading.Thread:
        def indefinite_tx():
            while not self.__thread_flag.is_set():
                self.__broadcast_next()
                time.sleep(self.__period)

        thr = threading.Thread(
            target=indefinite_tx,
            daemon=True
        )
        thr.start()
        return thr

    def __listen_next(self):
        data: tuple[MessageProtocol, Any] = udp_sock_recvfrom(self.__listener, 1024)
        return data

    def __start_listen(self, callback: Callable[[MessageProtocol], None] | None) -> threading.Thread:
        def indefinite_rx():
            while not self.__thread_flag.is_set():
                rx, addr = self.__listen_next()
                if callback and rx and isinstance(rx, MessageProtocol) and rx != self.__message:
                    rx.src.address = addr
                    callback(rx)

        thr = threading.Thread(
            target=indefinite_rx,
            daemon=True
        )
        thr.start()
        return thr

    def stop(self):
        self.__thread_flag.set()
        self.__broadcast_thread.join()
        self.__listener_thread.join()
        self.__broadcaster.close()
        self.__listener.close()

    def __del__(self):
        logger.info('Closing broadcaster\'s sockets...')
        self.stop()

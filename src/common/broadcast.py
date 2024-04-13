from . import serialize, deserialize, logger, new_socket, udp_sock_send, udp_sock_recv
import socket
import threading


class UdpBroadcast:
    def __init__(self,
                 broadcast_message,
                 broadcast_address: str = '255.255.255.255',
                 broadcast_port: int = 50001):
        self.__message = serialize(broadcast_message)
        self.__address = broadcast_address
        self.__port = broadcast_port
        self.__clients = []

        self.__create_sockets()
        logger.info('Broadcasting sockets has been created!')

        self.__listener_thread = threading.Thread(
            target=self.__listener_handler,
            daemon=True
        )

    def __create_sockets(self):
        self.__talker = new_socket('udp')
        self.__talker.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__talker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.__listener = new_socket('udp')
        self.__listener.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__listener.bind(('', self.__port))

    def broadcast(self):
        udp_sock_send(self.__talker, (self.__address, self.__port), self.__message)

    def listen(self):
        self.__listener_thread.start()

    def __listener_handler(self):
        while True:
            message, addr = udp_sock_recv(self.__listener, 1024)
            print('Received message: %s from %s' % (deserialize(message), addr))

    def close(self):
        self.__talker.close()
        self.__listener.close()

    def __del__(self):
        logger.info('Closing broadcaster\'s sockets...')
        self.close()

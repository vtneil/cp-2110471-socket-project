from .. import *
from . import TcpServer

import threading


class ChatServer:
    def __init__(self, address: tuple[str, int]):
        self.__clients: dict[str, User] = {}
        self.__groups: dict[str, set[str]] = {}

        self.__server = TcpServer(*address)

        self.__server_thread = threading.Thread(target=self.__start, daemon=True)
        self.__server_thread.start()

    def __start(self):
        with self.__server as server:
            server.start(self.__handle_chat_private)

    def __handle_chat_private(self, sock: socket.socket, addr: tuple[str, int]):
        this_clients: list[str | None] = [None]

        try:
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                message: Message = deserialize(data)
                logger.info(f'Received from {addr}: {message}')

                if not message:
                    raise ValueError('Message is empty!')

                if not isinstance(message, Message):
                    raise TypeError('Message is invalid!')

                # Response to messages
                __proc = None
                if MessageType.is_instruction(message.message_type):
                    __proc = self.__process_instruction
                elif this_clients[0] is not None:
                    __proc = self.__process_data

                if __proc is not None:
                    __proc(this_clients, addr, sock, message)

        except socket.error:
            logger.warning('Connection is forcibly reset by the client!')

        except Exception as e:
            logger.error(f'An error has occurred: {e}')

        finally:
            # Clean up when client closed the connections or error has occurred
            if this_clients[0] in self.__clients:
                # Leave group list
                for group in self.__groups:
                    self.__groups[group].discard(this_clients[0])

                # Leave client list
                self.__clients.pop(this_clients[0])
                sock.close()
                logger.info(f'Connection closed with {addr}')
                logger.info(f'{self.__clients}')

    def __process_instruction(self,
                              clients: list[str | None],
                              addr: tuple[str, int] | None,
                              sock: socket.socket,
                              message: Message):
        if message.message_type == MessageType.INSTRUCTION.IDENTIFY:
            if not (message.src and message.src.username):
                return

            clients[0] = message.src.username
            self.__clients[clients[0]] = new_user(username=clients[0],
                                                  group=None,
                                                  address=addr,
                                                  sock=sock)

            send_to_sock(sock, new_message(
                src=None,
                dst=message.src,
                message_type=MessageType.INSTRUCTION.RESPONSE,
                data=Response.OK
            ))

            if message.src not in self.__clients:
                logger.info('Client joined successfully!')
            else:
                logger.warning('Client name already exists!')

            logger.info(f'{self.__clients}')

        else:
            # Exit if not identified or unknown client
            if not (message.src and message.src.username and message.src.username in self.__clients):
                logger.warning('Source client not found!')
                return

            # todo
            if message.message_type == MessageType.INSTRUCTION.CLIENT.LIST:
                pass
            elif message.message_type == MessageType.INSTRUCTION.GROUP.LIST_GROUPS:
                pass
            elif message.message_type == MessageType.INSTRUCTION.GROUP.LIST_CLIENTS:
                pass
            elif message.message_type == MessageType.INSTRUCTION.GROUP.JOIN:
                pass
            elif message.message_type == MessageType.INSTRUCTION.GROUP.LEAVE:
                pass

    def __process_data(self,
                       clients: list[str | None],
                       addr: tuple[str, int] | None,
                       sock: socket.socket,
                       message: Message):
        # Exit if not identified
        if not (message.dst and message.dst.username and message.dst.username in self.__clients):
            logger.warning('Destination client not found!')
            return

        if message.dst and message.dst.group and message.dst.group in self.__groups:
            # GROUP CHAT
            logger.info(f'Group chat broadcast for Group {message.dst.group}')
            for client_name in self.__groups[message.dst.group]:
                logger.info(f'Direct messaging from {message.src.username} to {client_name}...')
                send_to_sock(self.__clients[client_name].sock, message)

        else:
            # PRIVATE CHAT
            logger.info(f'Direct messaging from {message.src.username} to {message.dst.username}...')
            send_to_sock(self.__clients[message.dst.username].sock, message)

    def wait(self):
        self.__server_thread.join()

    @property
    def clients(self):
        return self.__clients

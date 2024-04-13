from .. import *
from . import TcpServer

import threading
import socket


class ChatServer:
    def __init__(self, address: tuple[str, int]):
        self.__clients: dict[str, User] = {}
        self.__locks: dict[str, threading.Lock] = {}
        self.__groups: dict[str, set[str]] = {}

        self.__server = TcpServer(*address)

        self.__server_thread = threading.Thread(target=self.__start, daemon=True)
        self.__server_thread.start()

    def __start(self):
        with self.__server as server:
            server.start(self.__handle_message)

    def __handle_message(self, sock: socket.socket, addr: tuple[str, int]):
        this_clients: list[str | None] = [None]

        try:
            while True:
                message: MessageProtocol | None = None
                try:
                    message = tcp_sock_recv(sock, timeout=None)
                    logger.info(f'Received from {addr}: {message}')

                except socket.timeout:
                    logger.exception(f'Client timeout!')

                except EOFError:
                    break

                if not message:
                    continue

                if not isinstance(message, MessageProtocol):
                    raise TypeError('Message is invalid!')

                # Response to messages
                __message_processor = None
                if MessageProtocolCode.is_instruction(message.message_type):
                    __message_processor = self.__process_instruction
                elif this_clients[0] is not None:
                    __message_processor = self.__process_data

                if __message_processor is not None:
                    __message_processor(this_clients, addr, sock, message)

        except socket.error:
            logger.warning('Connection is forcibly reset by the client!')

        except Exception as e:
            logger.exception(f'An error has occurred: {e}')

        finally:
            # Clean up when client closed the connections or error has occurred
            if this_clients[0] in self.__clients:
                # Leave group list
                for group in self.__groups:
                    self.__groups[group].discard(this_clients[0])

                # Close the socket
                sock.close()
                logger.info(f'Connection closed with {addr}')

                # Leave client list
                if this_clients[0] in self.__clients:
                    self.__locks.pop(this_clients[0])
                if this_clients[0] in self.__clients:
                    self.__clients.pop(this_clients[0])

                # Clear empty groups inefficiently
                self.__groups: dict[str, set[str]] = {k: v for k, v in self.__groups.items() if v}

                logger.info(f'{self.__clients}')
                logger.info(f'{self.__groups}')

    def __process_instruction(self,
                              clients: list[str | None],
                              addr: tuple[str, int] | None,
                              sock: socket.socket,
                              message: MessageProtocol):
        if message.message_type == MessageProtocolCode.INSTRUCTION.IDENTIFY_MASTER:
            # Initial identification

            # Exit if invalid source
            if not (message.src and message.src.username):
                return

            if message.src.username not in self.__clients:
                # New client
                clients[0] = message.src.username
                self.__clients[clients[0]] = new_user(username=clients[0],
                                                      group=None,
                                                      address=addr,
                                                      sock_master=sock,
                                                      sock_slave=None)
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                    response=MessageProtocolResponse.OK,
                    body=None
                ))
                logger.info('Client joined successfully!')
            else:
                # Client already existed
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                    response=MessageProtocolResponse.ERROR,
                    body=None
                ))
                logger.warning('Client name already exists!')

            logger.info(f'{self.__clients}')

        elif message.message_type == MessageProtocolCode.INSTRUCTION.IDENTIFY_SLAVE:
            # Initial identification for slave socket

            # Exit if invalid source
            if not (message.src and message.src.username):
                return

            if message.src.username not in self.__clients:
                # Client not found
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                    response=MessageProtocolResponse.NOT_EXIST,
                    body=None
                ))
                logger.warning('Client master not found! Unable to add slave')
            else:
                # Add sock and new lock
                clients[0] = message.src.username
                self.__clients[clients[0]].sock_slave = sock
                self.__locks[clients[0]] = threading.Lock()
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                    response=MessageProtocolResponse.OK,
                    body=None
                ))
                logger.info('Client slave joined successfully!')

            logger.info(f'{self.__clients}')

        else:
            # Other instructions later after identification
            # Exit if not identified or unknown client
            if not (message.src and message.src.username and message.src.username in self.__clients):
                logger.warning('Source client not found!')
                return

            if message.message_type == MessageProtocolCode.INSTRUCTION.CLIENT.LIST:
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.DATA.PYTHON_OBJECT,
                    response=MessageProtocolResponse.OK,
                    body=list(self.__clients.keys())
                ))

            elif message.message_type == MessageProtocolCode.INSTRUCTION.GROUP.LIST_GROUPS:
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.DATA.PYTHON_OBJECT,
                    response=MessageProtocolResponse.OK,
                    body=list(self.__groups.keys())
                ))

            elif message.message_type == MessageProtocolCode.INSTRUCTION.GROUP.LIST_CLIENTS:
                body = message.body
                if body and isinstance(body, str) and body in self.__groups:
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.DATA.PYTHON_OBJECT,
                        response=MessageProtocolResponse.OK,
                        body=list(self.__groups[body])
                    ))
                else:
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.DATA.PYTHON_OBJECT,
                        response=MessageProtocolResponse.ERROR,
                        body=[]
                    ))

            elif message.message_type == MessageProtocolCode.INSTRUCTION.GROUP.CREATE:
                body = message.body
                if body and isinstance(body, str):
                    # Create a group if not exist
                    if body in self.__groups:
                        tcp_sock_send(sock, new_message(
                            src=None,
                            dst=message.src,
                            message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                            response=MessageProtocolResponse.EXISTS,
                            body=None
                        ))
                    # Throws error if exists
                    else:
                        self.__groups[body] = set()

                        # Reply successful message
                        tcp_sock_send(sock, new_message(
                            src=None,
                            dst=message.src,
                            message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                            response=MessageProtocolResponse.OK,
                            body=None
                        ))
                else:
                    # Reply error message
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                        response=MessageProtocolResponse.ERROR,
                        body=None
                    ))
                logger.info(f'{self.__clients}')
                logger.info(f'{self.__groups}')

            elif message.message_type == MessageProtocolCode.INSTRUCTION.GROUP.JOIN:
                body = message.body
                if body and isinstance(body, str) and body in self.__groups:
                    # Add user to that group
                    self.__groups[body].add(message.src.username)
                    self.__clients[clients[0]].group = body

                    # Reply successful message
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                        response=MessageProtocolResponse.OK,
                        body=None
                    ))
                else:
                    # Reply error message
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                        response=MessageProtocolResponse.ERROR,
                        body=None
                    ))

                logger.info(f'{self.__clients}')
                logger.info(f'{self.__groups}')

            elif message.message_type == MessageProtocolCode.INSTRUCTION.GROUP.LEAVE:
                # Remove user from specific group
                body = message.body
                if body and isinstance(body, str) and body in self.__groups:
                    if message.src.username in self.__groups[body]:
                        self.__groups[body].discard(message.src.username)

                        # Clear if empty
                        if not self.__groups[body]:
                            self.__groups.pop(body)

                        # Unassign group from user
                        self.__clients[clients[0]].group = None

                        # Reply successful message
                        tcp_sock_send(sock, new_message(
                            src=None,
                            dst=message.src,
                            message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                            response=MessageProtocolResponse.OK,
                            body=None
                        ))
                    else:
                        # Reply error message (not exist)
                        tcp_sock_send(sock, new_message(
                            src=None,
                            dst=message.src,
                            message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                            response=MessageProtocolResponse.NOT_EXIST,
                            body=None
                        ))
                else:
                    # Reply error message
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                        response=MessageProtocolResponse.ERROR,
                        body=None
                    ))

                logger.info(f'{self.__clients}')
                logger.info(f'{self.__groups}')

            elif message.message_type == MessageProtocolCode.INSTRUCTION.GROUP.LEAVE_ALL:
                # Remove user from every group
                for group in self.__groups:
                    self.__groups[group].discard(message.src.username)

                # Clear empty groups
                self.__groups: dict[str, set[str]] = {k: v for k, v in self.__groups.items() if v}

                # Unassign group from user
                self.__clients[clients[0]].group = None

                # Always reply successful message
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                    response=MessageProtocolResponse.OK,
                    body=None
                ))

                logger.info(f'{self.__clients}')
                logger.info(f'{self.__groups}')

    def __process_data(self,
                       clients: list[str | None],
                       addr: tuple[str, int] | None,
                       sock: socket.socket,
                       message: MessageProtocol):
        source_exists: bool = message.src and message.src.username and message.src.username in self.__clients

        # Exit if not identified
        if not source_exists:
            logger.warning('Source client not found!')
            return

        destination_is_group: bool = message.dst and message.dst.group and message.dst.group in self.__groups
        destination_is_private: bool = message.dst and message.dst.username and message.dst.username in self.__clients
        user_is_in_group: bool = (message.src.group in self.__groups and
                                  message.src.username in self.__groups[message.src.group])

        if destination_is_group:
            # WANT TO SEND IN A GROUP CHAT
            if not user_is_in_group:
                logger.warning(f'User {message.src.username} is not in the group!')
                return

            logger.info(f'Group chat broadcast for Group {message.dst.group}')
            for target_client in self.__groups[message.dst.group]:
                if target_client == message.src.username:
                    continue

                with self.__locks[target_client]:
                    logger.info(
                        f'Direct messaging from {message.src.username} to {message.dst.group}/{target_client}...')
                    tcp_sock_send(self.__clients[target_client].sock_slave, message)

                    # Always reply successful message when done
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                        response=MessageProtocolResponse.OK,
                        body=None
                    ))

        elif destination_is_private:
            if message.src.username != message.dst.username:
                with self.__locks[message.dst.username]:
                    # WANT TO SEND PRIVATE CHAT
                    logger.info(f'Direct messaging from {message.src.username} to {message.dst.username}...')
                    tcp_sock_send(self.__clients[message.dst.username].sock_slave, message)

                    # Always reply successful message when done
                    tcp_sock_send(sock, new_message(
                        src=None,
                        dst=message.src,
                        message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                        response=MessageProtocolResponse.OK,
                        body=None
                    ))
            else:
                logger.info(f'Client loopback tried by: {message.src.username}')
                tcp_sock_send(sock, new_message(
                    src=None,
                    dst=message.src,
                    message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                    response=MessageProtocolResponse.ERROR,
                    body=None
                ))

        else:
            # INVALID DESTINATION
            logger.warning(f'Destination client not found!')

            # Reply error message
            tcp_sock_send(sock, new_message(
                src=None,
                dst=message.src,
                message_type=MessageProtocolCode.INSTRUCTION.RESPONSE,
                response=MessageProtocolResponse.ERROR,
                body=None
            ))

    def wait(self):
        self.__server_thread.join()

    @property
    def clients(self):
        return self.__clients

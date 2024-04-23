import functools
import threading
from typing import Any, Callable
import queue

from .. import *
from . import TcpClient
from app.common.types import *


def single(func):
    @functools.wraps(func)
    def wrapper(cls, *args, **kwargs):
        with cls.sock_lock:
            return func(cls, *args, **kwargs)

    return wrapper


class ChatAgent:
    def __init__(self,
                 client_name: str,
                 remote_address: tuple[str, int],
                 open_sockets: int = 64,
                 recv_callback: Callable[[MessageProtocol], None] | None = None,
                 disc_callback: Callable[[MessageProtocol], None] | None = None):
        """
        A simple chat agent (client side backend)

        :param client_name: Client name (name to join)
        :param open_sockets: Number of socket to open for concurrent data receive
        :param recv_callback: Callback function on data receive (What to do with data?)
        :param disc_callback: Callback function on local network discovery (What to do if I discover another device?)
        """
        # Agent user
        self.__user = new_user(username=client_name, group=None, address=None, sock_slaves=None)

        # Master client: for control transactions
        logger.info('Setting up connections for you...')
        self.__master_client = TcpClient(client_name, remote_address[0], remote_address[1])

        # Guard test connection before proceeding
        if not self.__master_client.status:
            raise ConnectionError('Connection with the server failed!')

        self.__slave_clients = [TcpClient(client_name, remote_address[0], remote_address[1]) for _ in
                                range(open_sockets)]
        self.__sock_lock = threading.Lock()

        # Identification with server
        try:
            if not self.__identify():
                raise PermissionError('You are not allowed to use that client name!')
        except Exception:
            raise ConnectionError('Incorrect socket for server!')

        # Slave client: for receiving data
        self.__slave_flag = threading.Event()
        self.__receive_buffer: Buffer[MessageProtocol] = Buffer()
        self.__slave_orchestrator, self.__slave_threads = self.__start_receive(recv_callback)

        # Local network broadcast
        self.__broadcaster = UdpBroadcast(service_name=client_name,
                                          broadcast_mode=MessageProtocolCode.INSTRUCTION.BROADCAST.CLIENT_DISC,
                                          disc_callback=disc_callback)

        # Stop flag
        self.__is_stop = False

        logger.info('Chat agent is successfully initialized!')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __del__(self):
        self.stop()

    def stop(self):
        try:
            if not self.__is_stop:
                self.__is_stop = True
                logger.info('Stopping slave threads...')
                self.__slave_flag.set()
                self.__slave_orchestrator.join()
                for thr in self.__slave_threads:
                    thr.join()
                self.__broadcaster.stop()
        except Exception:
            pass

    @property
    def username(self):
        return self.__user.username

    @property
    def sock_lock(self):
        return self.__sock_lock

    @single
    def __identify(self):
        # Identify master socket
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.IDENTIFY_MASTER,
            body=None
        ))

        if response.response != MessageProtocolResponse.OK:
            return False

        # Join slave sockets
        for slave in self.__slave_clients:
            response: MessageProtocol = slave.transaction(new_message_proto(
                src=self.__user,
                dst=None,
                message_type=MessageProtocolCode.INSTRUCTION.JOIN_SLAVE,
                body=None
            ))

            if response.response != MessageProtocolResponse.OK:
                return False

        # Identify slave sockets
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.IDENTIFY_SLAVES,
            body=None
        ))

        if response.response != MessageProtocolResponse.OK:
            return False

        return True

    @single
    def get_connected_clients(self) -> tuple[MessageProtocolResponse, list[str]]:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.CLIENT.LIST,
            body=None
        ))

        return response.response, response.body

    @single
    def get_groups(self) -> tuple[MessageProtocolResponse, list[str]]:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.LIST_GROUPS,
            body=None
        ))

        return response.response, response.body

    @single
    def get_clients_in_group(self, group_name: str) -> tuple[MessageProtocolResponse, list[str]]:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.LIST_CLIENTS,
            body=group_name
        ))

        return response.response, response.body

    @single
    def create_group(self, group_name: str) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.CREATE,
            body=group_name
        ))

        return response.response

    @single
    def join_group(self, group_name: str) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.JOIN,
            body=group_name
        ))

        if response.response == MessageProtocolResponse.OK:
            self.__user.group = group_name

        return response.response

    @single
    def create_and_join(self, group_name: str) -> tuple[MessageProtocolResponse, MessageProtocolResponse]:
        return self.create_group(group_name), self.join_group(group_name)

    @single
    def leave_group(self, group_name: str) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.LEAVE,
            body=group_name
        ))

        if response.response == MessageProtocolResponse.OK:
            self.__user.group = None

        return response.response

    @single
    def leave_all_groups(self) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.LEAVE_ALL,
            body=None
        ))

        if response.response == MessageProtocolResponse.OK:
            self.__user.group = None

        return response.response

    @single
    def send_private(self,
                     recipient: str,
                     data_type: MessageProtocolCode.Data,
                     data: Any) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=new_user(username=recipient, group=None),
            message_type=data_type,
            body=data
        ))

        return response.response

    @single
    def send_group(self,
                   group_name: str,
                   data_type: MessageProtocolCode.Data,
                   data: Any) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=new_user(username=None, group=group_name),
            message_type=data_type,
            body=data
        ))

        return response.response

    @single
    def announce(self,
                 data: str) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message_proto(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.DATA.PLAIN_TEXT,
            flag=MessageProtocolFlag.ANNOUNCE,
            body=data
        ))

        return response.response

    def __start_receive(self,
                        callback: Callable[[MessageProtocol], None] | None
                        ) -> tuple[threading.Thread, list[threading.Thread]]:
        def message_receive(client: TcpClient):
            if not callback:
                return

            # Put in queue
            while not self.__slave_flag.is_set():
                rx = client.receive()
                if rx and isinstance(rx, MessageProtocol):
                    self.__receive_buffer.put(rx)

        def message_orchestration():
            if not callback:
                return

            # Get from queue and call the callback function
            while not self.__slave_flag.is_set():
                while not self.__receive_buffer.empty():
                    data = self.__receive_buffer.get()
                    try:
                        callback(data)
                    except Exception:
                        pass

        threads = [threading.Thread(
            target=message_receive,
            args=(client,),
            daemon=True
        ) for client in self.__slave_clients]

        for thr in threads:
            thr.start()

        orchestrator = threading.Thread(
            target=message_orchestration,
            daemon=True
        )

        orchestrator.start()

        return orchestrator, threads

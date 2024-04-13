import functools
import socket
import threading
from typing import Any, Callable

from .. import UdpBroadcast
from .. import new_user, new_message
from .. import logger
from .. import MessageProtocol, MessageProtocolCode, MessageProtocolResponse
from . import TcpClient, UdpClient
from . import REMOTE_HOST, REMOTE_TCP_PORT, REMOTE_UDP_PORT


def single(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.sock_lock:
            return func(self, *args, **kwargs)

    return wrapper


class ChatAgent:
    def __init__(self,
                 client_name: str,
                 recv_callback: Callable[[MessageProtocol], None] | None = None):
        # Master client: for control from client
        self.__master_client = TcpClient(client_name, REMOTE_HOST, REMOTE_TCP_PORT)

        # Slave client: for control from server
        self.__slave_client = TcpClient(client_name, REMOTE_HOST, REMOTE_TCP_PORT)

        self.__broadcaster = UdpBroadcast(client_name)
        self.__user = new_user(username=client_name, group=None, address=None, sock_slave=None)
        self.__sock_lock = threading.Lock()

        self.__slave_flag = threading.Event()
        self.__slave_thread = self.__start_receive(recv_callback)

        if not self.__identify():
            raise PermissionError('You are not allowed to use that client name!')

    def __del__(self):
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def stop(self):
        logger.info('Stopping slave thread...')
        self.__slave_flag.set()
        self.__slave_thread.join()

    @property
    def sock_lock(self):
        return self.__sock_lock

    @single
    def __identify(self):
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.IDENTIFY_MASTER,
            body=None
        ))

        if response.response != MessageProtocolResponse.OK:
            return False

        response: MessageProtocol = self.__slave_client.transaction(new_message(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.IDENTIFY_SLAVE,
            body=None
        ))

        if response.response != MessageProtocolResponse.OK:
            return False

        return True

    @single
    def get_connected_clients(self) -> tuple[MessageProtocolResponse, list[str]]:
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.CLIENT.LIST,
            body=None
        ))

        return response.response, response.body

    @single
    def get_groups(self) -> tuple[MessageProtocolResponse, list[str]]:
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.LIST_GROUPS,
            body=None
        ))

        return response.response, response.body

    @single
    def get_clients_in_group(self, group_name: str) -> tuple[MessageProtocolResponse, list[str]]:
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.LIST_CLIENTS,
            body=group_name
        ))

        return response.response, response.body

    @single
    def create_group(self, group_name: str) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=None,
            message_type=MessageProtocolCode.INSTRUCTION.GROUP.CREATE,
            body=group_name
        ))

        return response.response

    @single
    def join_group(self, group_name: str) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message(
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
        response: MessageProtocol = self.__master_client.transaction(new_message(
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
        response: MessageProtocol = self.__master_client.transaction(new_message(
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
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=new_user(username=recipient, group=None),
            message_type=data_type,
            body=data
        ))

        return response.response

    @single
    def send_group(self,
                   group_name,
                   data_type: MessageProtocolCode.Data,
                   data: Any) -> MessageProtocolResponse:
        response: MessageProtocol = self.__master_client.transaction(new_message(
            src=self.__user,
            dst=new_user(username=None, group=group_name),
            message_type=data_type,
            body=data
        ))

        return response.response

    def __receive_next(self):
        response: MessageProtocol = self.__slave_client.receive()
        return response

    def __start_receive(self, callback: Callable[[MessageProtocol], None] | None) -> threading.Thread:
        def indefinite_rx():
            while True:
                if self.__slave_flag.is_set():
                    return
                rx = self.__receive_next()
                if rx and callback:
                    callback(rx)

        thr = threading.Thread(
            target=indefinite_rx,
            daemon=True
        )
        thr.start()
        return thr

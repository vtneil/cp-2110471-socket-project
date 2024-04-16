import functools
import os
import socket
import time
import sys
import datetime

from app.common import *
from app.common.client import *


def suppress(func):
    """
    Suppress static method warning
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class ProgramQuitException(Exception):
    pass


class AppCLI:
    def __init__(self,
                 client_name: str,
                 remote_address: tuple[str, int],
                 open_sockets: int = 64,
                 app_name: str = 'Chat App (CLI)'):
        # App Parameters
        self.__agent_client_name = client_name
        self.__agent_remote_address = remote_address
        self.__agent_open_sockets = open_sockets

        # Local devices
        self.__local_clients: dict[str, tuple[float, tuple[str, int]]] = {}
        self.__local_servers: dict[str, tuple[float, tuple[str, int]]] = {}

        # Program argument parser (CLI)
        self.__src: tuple[str | None, str | None] = (None, None)
        self.__parser = ProgramArgumentParser(app_name=app_name)
        self.__prev_cmd = ''
        self.__setup_parser()

    def __setup_parser(self):
        self.__parser.add_commands(
            ProgramCommand(
                'list', 'List query',
                ProgramCommandArgument(
                    name='option',
                    help_str='What to list?',
                    data_type=str,
                    choices=['clients', 'groups', 'members', 'local'],
                    optional=True
                ), callback=self.__cmd_list,
                aliases=['ls']
            ),
            ProgramCommand(
                'chat', 'Private message with someone',
                ProgramCommandArgument(
                    name='recipient',
                    help_str='Recipient',
                    data_type=str,
                    long_string=True
                ), callback=self.__cmd_chat,
                aliases=['pm']
            ),
            ProgramCommand(
                'create', 'Create a new group (chatroom)',
                ProgramCommandArgument(
                    name='name',
                    help_str='Group name',
                    data_type=str,
                    long_string=True
                ), callback=self.__cmd_group_create,
                aliases=['new']
            ),
            ProgramCommand(
                'join', 'Join a group (chatroom)',
                ProgramCommandArgument(
                    name='name',
                    help_str='Group name',
                    data_type=str,
                    long_string=True
                ), callback=self.__cmd_group_join,
                aliases=['jam']
            ),
            ProgramCommand(
                'leave', 'Leave the group (chatroom)',
                ProgramCommandArgument(
                    name='option',
                    help_str='Leave or leave all',
                    data_type=str,
                    choices=['all'],
                    optional=True
                ),
                callback=self.__cmd_group_leave,
                aliases=['bye']
            ),
            ProgramCommand(
                'send', 'Send message to the recipient/group',
                ProgramCommandArgument(
                    name='message',
                    help_str='Message to send',
                    data_type=str,
                    long_string=True
                ),
                callback=self.__cmd_send_text,
                aliases=['message', 'msg', 'm']
            ),
            ProgramCommand(
                'file', 'Send file to the recipient/group',
                ProgramCommandArgument(
                    name='path',
                    help_str='File path to send',
                    data_type=str,
                    long_string=True
                ),
                callback=self.__cmd_send_file,
                aliases=['send-file', 'f']
            ),
            ProgramCommand(
                'quit', 'Exit the application',
                callback=self.__cmd_quit,
                aliases=['exit', 'q']
            )
        )

    def run(self):
        with ChatAgent(
                client_name=self.__agent_client_name,
                remote_address=self.__agent_remote_address,
                open_sockets=self.__agent_open_sockets,
                recv_callback=AppCLI.on_receive,
                disc_callback=self.__on_discovery
        ) as self.__agent:
            while True:
                time.sleep(0.25)
                if self.__src[0]:
                    prompt_str = self.__construct_sys_prompt(f'{self.__agent.username} [Group: {self.__src[0]}]')
                elif self.__src[1]:
                    prompt_str = self.__construct_sys_prompt(f'{self.__agent.username} [To: {self.__src[1]}]')
                else:
                    prompt_str = self.__construct_sys_prompt(f'{self.__agent.username}')

                try:
                    cmd_input = input(prompt_str).split()
                except KeyboardInterrupt:
                    break

                if cmd_input == '!!':
                    cmd_input = self.__prev_cmd
                self.__prev_cmd = cmd_input

                try:
                    if not self.__parser.execute(cmd_input):
                        print("No command provided. Type 'quit' to exit.")
                except ProgramQuitException:
                    break
                except SystemExit:
                    continue

    @suppress
    def __on_discovery(self, message: MessageProtocol):
        if not (message and isinstance(message, MessageProtocol)):
            return

        # Adding
        if message.message_type == MessageProtocolCode.INSTRUCTION.BROADCAST.SERVER_DISC:
            self.__local_servers[message.src.username] = time.time(), message.src.address
        elif message.message_type == MessageProtocolCode.INSTRUCTION.BROADCAST.CLIENT_DISC:
            self.__local_clients[message.src.username] = time.time(), message.src.address
        else:
            return

        # Cleanup
        tim_callback = time.time()
        for server in list(self.__local_servers.keys()):
            if tim_callback - self.__local_servers[server][0] >= 5.0:
                self.__local_servers.pop(server)
        for client in list(self.__local_clients.keys()):
            if tim_callback - self.__local_clients[client][0] >= 5.0:
                self.__local_clients.pop(client)

        # print(f'Discovered a device: \"{message.src.username}\" at {message.src.address}')
        # print(self.__local_servers)
        # print(self.__local_clients)

    @suppress
    def __cmd_list(self, args):
        if not args.option or args.option == 'clients':
            res = self.__agent.get_connected_clients()[1]
            if res:
                print('Connected clients at your connected server')
                for i, c in enumerate(res):
                    print(f'[{i:4d}] {c}')
            else:
                print('No client is connected!')

        elif args.option == 'groups':
            res = self.__agent.get_groups()[1]
            if res:
                print('Available groups')
                for i, c in enumerate(res):
                    print(f'[{i:4d}] {c}')
            else:
                print('No group in your connected server yet!')

        elif args.option == 'members':
            res = self.__agent.get_clients_in_group(self.__src[0])[1]
            if res:
                print(f'Members in group \"{self.__src[0]}\"')
                for i, c in enumerate(res):
                    print(f'[{i:4d}] {c}')
            else:
                print('No client is in the group!')

        elif args.option == 'local':
            if self.__local_servers:
                print(f'Local servers in your network')
                for i, (name, addr) in enumerate(self.__local_servers.items()):
                    print(f'[{i:4d}] {name} at {addr[1][0]}:{addr[1][1]}')
            else:
                print('(No local servers in your network)')
            if self.__local_clients:
                print(f'Local clients in your network')
                for i, (name, addr) in enumerate(self.__local_clients.items()):
                    print(f'[{i:4d}] {name} at {addr[1][0]}:{addr[1][1]}')
            else:
                print('(No local clients in your network)')
        return 0

    @suppress
    def __cmd_chat(self, args):
        recipient = ' '.join(args.recipient)
        self.__src = (None, recipient)
        return 0

    @suppress
    def __cmd_group_create(self, args):
        name = ' '.join(args.name)
        if self.__agent.create_group(name) == MessageProtocolResponse.OK:
            print(f'Created group {name}!')
            return 0
        else:
            print(f'Unable to create the group')
            return 1

    @suppress
    def __cmd_group_join(self, args):
        name = ' '.join(args.name)
        if self.__agent.join_group(group_name=name) == MessageProtocolResponse.OK:
            self.__src = (name, None)
            print(f'Joined group: {self.__src[0]}')
            return 0
        else:
            print(f'Error joining group: {self.__src[0]} (Doesn\'t exist)')
            return 1

    @suppress
    def __cmd_group_leave(self, args):
        if args.option:
            self.__agent.leave_group(self.__src[0])
        else:
            self.__agent.leave_all_groups()

        self.__src = (None, self.__src[1])
        return 0

    @suppress
    def __cmd_send_text(self, args):
        message = ' '.join(args.message)
        if self.__src[0]:
            self.__agent.send_group(group_name=self.__src[0],
                                    data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                    data=message)
        else:
            self.__agent.send_private(recipient=self.__src[1],
                                      data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                      data=message)
        return 0

    @suppress
    def __cmd_send_file(self, args):
        file_path: str = ' '.join(args.path)
        if os.path.isfile(file_path):
            with open(file_path, mode='rb') as f:
                file_content: bytes = f.read()
                file_proto = new_file_proto(filename=os.path.basename(file_path),
                                            content=file_content)
                if self.__src[0]:
                    self.__agent.send_group(group_name=self.__src[0],
                                            data_type=MessageProtocolCode.DATA.FILE,
                                            data=file_proto)
                else:
                    self.__agent.send_private(recipient=self.__src[1],
                                              data_type=MessageProtocolCode.DATA.FILE,
                                              data=file_proto)
            return 0
        else:
            logger.error(f'File {file_path} doesn\'t exist!')
            return 1

    @suppress
    def __cmd_quit(self, _):
        raise ProgramQuitException

    @staticmethod
    def __construct_sys_prompt(s: str):
        return f'[{datetime_fmt()}] {s} > '

    @staticmethod
    def on_receive(message: MessageProtocol):
        if not isinstance(message, MessageProtocol) or not message.src:
            return

        if message.message_type == MessageProtocolCode.DATA.FILE:
            # Receive file
            _file_proto: FileProtocol = message.body
            print(f'[{datetime_fmt()}] {message.src.username}: '
                  f'Sent a file: {_file_proto.filename} '
                  f'(size: {_file_proto.size} bytes)')

            # Save file
            home_dir = os.path.expanduser("~").replace('\\', '/')
            filename = uniquify(f'{home_dir}/Downloads/socket/{_file_proto.filename}')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, mode='wb') as f:
                f.write(_file_proto.content)

            logger.info(f'File {_file_proto.filename} is saved as \"{filename}\".')

        else:
            # Other format
            print(f'[{datetime_fmt()}] {message.src.username}: {message.body}')

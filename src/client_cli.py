import os.path
import sys
import time
from typing import Callable, Any

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from common import *
from common.client import *

# Application globals
recipient: str | None = None
group: str | None = None


def construct_sys_prompt(s: str):
    return f'[{datetime_fmt()}] {s} > '


def list_clients(chat_agent: ChatAgent):
    res = chat_agent.get_connected_clients()[1]
    if res:
        print(construct_sys_prompt('Connected clients'))
        for i, c in enumerate(res):
            print(f'[{i:4d}] {c}')
    else:
        print('No client is connected!')
    return 0


def list_groups(chat_agent: ChatAgent):
    res = chat_agent.get_groups()[1]
    if res:
        print(construct_sys_prompt('Available groups'))
        for i, c in enumerate(res):
            print(f'[{i:4d}] {c}')
    else:
        print('No group in the server yet!')
    return 0


def list_members(chat_agent: ChatAgent, group_name: str):
    res = chat_agent.get_clients_in_group(group_name)[1]
    if res:
        print(construct_sys_prompt(f'Members in group \"{group_name}\"'))
        for i, c in enumerate(res):
            print(f'[{i:4d}] {c}')
    else:
        print('No client is in the group!')
    return 0


def create_group(chat_agent: ChatAgent, group_name: str):
    if chat_agent.create_group(group_name) == MessageProtocolResponse.OK:
        print(f'Created group {group_name}!')
    else:
        print(f'Unable to create the group')


def leave_group(chat_agent: ChatAgent, group_name: str):
    global group

    chat_agent.leave_group(group_name)
    group = None
    return 0


def leave_all(chat_agent: ChatAgent):
    global group

    chat_agent.leave_all_groups()
    group = None
    return 0


def execute(tokens: list[str],
            chat_agent: ChatAgent,
            fallback_callable: Callable[[], None] | None = None,
            *args, **kwargs) -> int:
    def print_help(*_):
        __helper_print_help()

    cli_map: dict[str, Callable[[ChatAgent, Any], int] | None] = {
        # General actions
        'ls': list_clients,
        'list-clients': list_clients,
        'list-groups': list_groups,
        'list-members': list_members,
        'exit': lambda _: -1,
        'quit': lambda _: -1,
        'help': print_help,

        # Private actions
        'chat': None,

        # Group actions
        'group-create': create_group,
        'group-join': None,
        'group-leave': leave_group,
        'group-leave-all': leave_all,

        # Chatroom actions
        'send': None,
        'send-file': None
    }

    def __helper_print_help():
        print('Available commands')
        for c in cli_map.keys():
            print(c)

    if len(tokens) < 1:
        return 255

    cmd = tokens[0]

    if cmd not in cli_map:
        logger.error(f'Unknown command: \"{cmd}\". Press help to see the list of commands')
        return 255

    try:
        if cli_map:
            return cli_map[cmd](chat_agent, *(tokens[1:]), *args, **kwargs)
        elif fallback_callable:
            fallback_callable()
        else:
            return 254
    except KeyboardInterrupt:
        return 2
    except Exception as e:
        logger.exception(f'Error: {e}')
        return 1


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


def on_discover(message: MessageProtocol):
    if message.message_type == MessageProtocolCode.INSTRUCTION.BROADCAST.CLIENT_DISC:
        print(f'Client Discovery [{datetime_fmt()}] {message.src.username} at {message.src.address}')
    elif message.message_type == MessageProtocolCode.INSTRUCTION.BROADCAST.SERVER_DISC:
        print(f'Server Discovery [{datetime_fmt()}] {message.src.username} at {message.src.address}')


if __name__ == '__main__':
    try:
        client_name = input('Client name > ').strip()
    except KeyboardInterrupt:
        sys.exit(0)

    time.sleep(0.5)

    with ChatAgent(client_name=client_name,
                   open_sockets=128,
                   recv_callback=on_receive,
                   disc_callback=None) as agent:
        prev_command = ''

        while True:
            if group:
                prompt_str = construct_sys_prompt(f'{client_name} [Group: {group}]')
            elif recipient:
                prompt_str = construct_sys_prompt(f'{client_name} [{recipient}]')
            else:
                prompt_str = construct_sys_prompt(f'{client_name}')

            try:
                command = input(prompt_str)
            except KeyboardInterrupt:
                break

            # Repeat
            if command == '!!':
                command = prev_command

            # Empty
            tok = tokenize(command)
            if len(tok) < 1:
                continue

            # Parse
            prev_command = command
            tok_cmd, *tok_args = tok

            try:
                if tok_cmd in ['chat', 'pm']:
                    recipient, group = tok_args[0], None

                elif tok_cmd == 'group-join':
                    if agent.join_group(group_name=tok_args[0]) == MessageProtocolResponse.OK:
                        recipient, group = None, tok_args[0]
                        print(f'Joined group: {group}')
                    else:
                        print(f'Error joining group: {group} (Doesn\'t exist)')

                elif tok_cmd == 'send':
                    if group:
                        agent.send_group(group_name=group,
                                         data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                         data=tok_args[0])
                    else:
                        agent.send_private(recipient=recipient,
                                           data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                           data=tok_args[0])

                elif tok_cmd == 'send-file':
                    file_path: str = tok_args[0]
                    if os.path.isfile(file_path):
                        with open(file_path, mode='rb') as f:
                            file_content: bytes = f.read()
                            file_proto = new_file_proto(filename=os.path.basename(file_path),
                                                        content=file_content)
                            if group:
                                agent.send_group(group_name=group,
                                                 data_type=MessageProtocolCode.DATA.FILE,
                                                 data=file_proto)
                            else:
                                agent.send_private(recipient=recipient,
                                                   data_type=MessageProtocolCode.DATA.FILE,
                                                   data=file_proto)
                    else:
                        logger.error(f'File {file_path} doesn\'t exist!')

                else:
                    code = execute(tok, chat_agent=agent)

                    if code == -1:  # Quit the program
                        break

                    if tok_cmd in ['group-leave', 'group-leave-all']:
                        group = None
            except Exception as e:
                logger.exception(f'Error: {e}')

        # Use with context "with" to automatically close
        logger.info('Bye!')

import sys
import time
from typing import Callable, Any

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from common import *
from common.client import *


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
    chat_agent.leave_group(group_name)
    return 0


def leave_all(chat_agent: ChatAgent):
    chat_agent.leave_all_groups()
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
    if message.src:
        print(f'[{datetime_fmt()}] {message.src.username}: {message.body}')


if __name__ == '__main__':
    client_name = input('Client name > ').strip()
    client_user = new_user(username=client_name, group=None, address=None, sock_slave=None)

    # or use with context "with" statement
    agent = ChatAgent(client_name=client_name,
                      recv_callback=on_receive)

    recipient = None
    group = None

    time.sleep(0.5)

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

        tok = tokenize(command)
        if len(tok) < 1:
            code = execute(tok, chat_agent=agent)
            if code == -1:  # Quit the program
                break
            continue
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

            else:
                code = execute(tok, chat_agent=agent)

                if code == -1:  # Quit the program
                    break

                if tok_cmd in ['group-leave', 'group-leave-all']:
                    group = None
        except Exception as e:
            logger.exception(f'Error: {e}')

    # Use with context "with" to automatically close
    agent.stop()
    logger.info('Bye!')

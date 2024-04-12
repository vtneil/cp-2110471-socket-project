import sys

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from common import *
from common.client import *

if __name__ == '__main__':
    group_name = None
    client_name = input('Client name: ').strip()
    target_name = input('Send to who?: ').strip()

    tcp_client = TcpClient(client_name, REMOTE_HOST, REMOTE_TCP_PORT)
    udp_client = UdpClient(client_name, REMOTE_HOST, REMOTE_TCP_PORT + 1)

    client_user = new_user(username=client_name, group=group_name, address=None, sock=None)
    target_user = new_user(username=target_name, group=group_name, address=None, sock=None)

    identifier = new_message(
        src=client_user,
        dst=None,
        message_type=MessageType.INSTRUCTION.IDENTIFY,
        data=None
    )
    tcp_client.send(identifier)

    status: Message = tcp_client.receive()

    msg = new_message(
        src=client_user,
        dst=target_user,
        message_type=MessageType.DATA.PLAIN_TEXT,
        data=None
    )

    role = input('Role: ').strip()

    if role == 'sender':
        while True:
            try:
                tx = input('To send: ').strip()
                msg.data = tx
                tcp_client.send(msg)

            except KeyboardInterrupt:
                print()
                break
    else:
        while True:
            rx: Message = tcp_client.receive()
            print(f'{rx.src.username}: {rx.data}')

    print('Ended')

    broadcaster = UdpClient(client_name, REMOTE_HOST, REMOTE_TCP_PORT)

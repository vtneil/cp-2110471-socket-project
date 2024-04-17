import sys
import socket

from app.lib import *
from app.common import *
from app.common.client import *

__version__ = '1.0.0'

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('Usage: python -m app.client_cli [HOST]:[PORT] [NUM_CONNECTIONS?]')
        print('                      HOST: Server Hostname/IP Address')
        print('                      PORT: Server Port')
        print('NUM_CONNECTIONS (Optional): Number of sockets to open')
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1].count(':') == 1:
        tmp = sys.argv[1].strip().split(':')
        remote_host_port: tuple[str, int] = tmp[0], int(tmp[1])

    else:
        remote_host_port: tuple[str, int] = (REMOTE_HOST, REMOTE_TCP_PORT)

    if len(sys.argv) > 2 and sys.argv[2]:
        try:
            num_connections = int(sys.argv[2])
        except ValueError:
            num_connections = 4
    else:
        num_connections = 4

    print(f'Connection will be made to {remote_host_port[0]}:{remote_host_port[1]} using {num_connections} sockets')

    try:
        client_name = input('Client name > ').strip()
    except KeyboardInterrupt:
        sys.exit(0)

    print('#' * 128)
    print('#' + ' ' * 126 + '#')
    print('#' + f'CP-2110471 SOCKET CHAT APPLICATION V{__version__}'.center(126) + '#')
    print('#' + ' ' * 126 + '#')
    print('#' + f'Welcome, {client_name}!'.center(126) + '#')
    print('#' + f'Type \"help\" in the command prompt for more info.'.center(126) + '#')
    print('#' + ' ' * 126 + '#')
    print('#' + f'DISCLAIMER: No guarantee of any kinds'.center(126) + '#')
    print('#' + ' ' * 126 + '#')
    print('#' * 128)

    try:
        app = AppCLI(app_name='app',
                     client_name=client_name,
                     remote_address=remote_host_port,
                     open_sockets=num_connections)
        app.run()
    except socket.socket:
        pass
    except KeyboardInterrupt:
        pass

    logger.info('Bye!')

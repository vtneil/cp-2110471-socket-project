import time
import sys
import socket

from app.lib import *
from app.common import *
from app.common.client import *

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].count(':') == 1:
        tmp = sys.argv[1].strip().split(':')
        remote_host_port: tuple[str, int] = tmp[0], int(tmp[1])

    else:
        remote_host_port: tuple[str, int] = (REMOTE_HOST, REMOTE_TCP_PORT)

    print(f'Connection will be made to {remote_host_port[0]}:{remote_host_port[1]}')

    try:
        client_name = input('Client name > ').strip()
    except KeyboardInterrupt:
        sys.exit(0)

    with ChatAgent(client_name=client_name,
                   remote_address=remote_host_port,
                   open_sockets=128,
                   recv_callback=AppCLI.on_receive,
                   disc_callback=None) as agent:
        app = AppCLI(app_name='app', agent=agent)
        try:
            app.run()
        except socket.socket:
            pass
        except KeyboardInterrupt:
            pass

    logger.info('Bye!')

import time
import sys
import socket

from app.lib import *
from app.common import *
from app.common.client import *

if __name__ == "__main__":
    try:
        client_name = input('Client name > ').strip()
    except KeyboardInterrupt:
        sys.exit(0)

    time.sleep(0.5)
    with ChatAgent(client_name=client_name,
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

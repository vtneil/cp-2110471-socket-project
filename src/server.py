import sys
import threading
from common.logger import logger

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from common.server import *


def start_server():
    with TcpServer(HOST, PORT) as server:
        server.start()


if __name__ == '__main__':
    logger.info('Starting server...')

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    server_thread.join()

    logger.info('Stopped server...')

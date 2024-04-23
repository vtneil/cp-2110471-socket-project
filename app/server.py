import sys
from app.common.logger import logger

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from app.common.server import *


def main():
    if len(sys.argv) > 1 and sys.argv[1].count(':') == 1:
        tmp = sys.argv[1].strip().split(':')
        host_port: tuple[str, int] = tmp[0], int(tmp[1])

    else:
        host_port: tuple[str, int] = (HOST, PORT)

    if len(sys.argv) > 2 and sys.argv[2]:
        server_name = sys.argv[2]
    else:
        server_name = 'Example chat server'

    logger.info('Starting server...')

    chat_server = ChatServer(address=host_port, server_name=server_name)

    try:
        while chat_server.is_alive():
            chat_server.wait(timeout=1.0)
    except KeyboardInterrupt:
        logger.info('Stopping server.')

    logger.info('Stopped server.')


if __name__ == '__main__':
    main()

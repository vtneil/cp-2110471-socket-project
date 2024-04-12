import sys
from common.logger import logger

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from common.server import *

if __name__ == '__main__':
    logger.info('Starting server...')

    chat_server = ChatServer((HOST, PORT))

    chat_server.wait()

    logger.info('Stopped server...')

from ..common import *
from .client_config import *

if __name__ == '__main__':
    # client_name = 'VT'
    # client = TcpClient(client_name, HOST, PORT)

    server = TcpServer(HOST, PORT)
    server.start()

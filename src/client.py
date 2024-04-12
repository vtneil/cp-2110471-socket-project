import sys
import ipaddress

if sys.version_info < (3, 12):
    raise Exception('Requires Python 3.12 or higher')

from common import *
from common.client import *

if __name__ == '__main__':
    client_name = 'VT'
    client = TcpClient(client_name, HOST, PORT)
    client.send('Hello')

    print(client.receive())
    print('Ended')

    broadcaster = UdpClient(client_name, HOST, PORT)

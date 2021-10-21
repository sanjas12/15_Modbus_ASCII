# print(__file__)

import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
'%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

UNIT = 0x1



import pymodbus
from pymodbus.transaction import ModbusAsciiFramer
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# print(pymodbus.__version__)


# dos     common                  IO       USB-BUS ( ACM => acm modem )
# name     name     major minor address || common name      common name
# COM1   /dev/ttyS0  4,  64;   3F8      || /dev/ttyUSB0  |  /dev/ttyACM0
# COM2   /dev/ttyS1  4,  65;   2F8      || /dev/ttyUSB1  |  /dev/ttyACM1
# COM3   /dev/ttyS2  4,  66;   3E8      || /dev/ttyUSB2  |  /dev/ttyACM2
# COM4   /dev/ttyS3  4,  67;   2E8      || /dev/ttyUSB3  |  /dev/ttyACM3
#  -     /dev/ttyS4  4,  68;   various

def run_sync_client():

    client = ModbusClient(method='ascii', port='COM1', timeout=10,
                          baudrate='9600', stopbits=1)

    client.connect()

    # print(str.encode('$AA'))

    client.send(str.encode('$01M'))
    # client.register(str.encode('$AA'))

    rr = client.recv(1024)

    # log.debug("Reading Coils")
    # rr = client.read_coils(1, 1, unit=UNIT)
    log.debug(rr)

    client.close()


if __name__ == '__main__':
    run_sync_client()

from pymodbus.client.sync import ModbusTcpClient as ModbusClient

ipadr = 'localhost'
ipadr = '192.168.110.2'
ipadr = '10.10.88.19'


import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

UNIT = 0x1


client = ModbusClient(ipadr, port=5020)
    # from pymodbus.transaction import ModbusRtuFramer
    # client = ModbusClient('localhost', port=5020, framer=ModbusRtuFramer)
    # client = ModbusClient(method='binary', port='/dev/ptyp0', timeout=1)
    # client = ModbusClient(method='ascii', port='/dev/ptyp0', timeout=1)
    # client = ModbusClient(method='rtu', port='/dev/ptyp0', timeout=1,
    #                       baudrate=9600)
client.connect()


log.debug("Reading Coils")
rr = client.read_coils(1, 1, unit=UNIT)
log.debug(rr)
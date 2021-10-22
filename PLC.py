from pyModbusTCP.client import ModbusClient
import time

SERVER_HOST = '10.10.88.19'
SERVER_PORT = 502
addr = 998
# data = [0]

c = ModbusClient()

# uncomment this line to see debug message
# c.debug(True)

# define modbus server host, port
c.host(SERVER_HOST)
c.port(SERVER_PORT)


def plc(data):
    # open or reconnect TCP to server
    if not c.is_open():
        if not c.open():
            print("unable to connect to "+SERVER_HOST+":"+str(SERVER_PORT))

    if c.is_open():
        is_ok = c.write_multiple_registers(addr, data)
        if is_ok:
            print(data[0], "write to PLC:")
        else:
            print(" unable to write ")
        time.sleep(0.5)
        data_read = c.read_holding_registers(addr, 1)

        print('data from PLC: ', data_read)

        # data[0] = data[0] + 3

        # print(data, bits)

    time.sleep(1)


if __name__ == '__main__':
    data = [0]
    while True:
        plc(data)
        data[0] = data[0] + 3

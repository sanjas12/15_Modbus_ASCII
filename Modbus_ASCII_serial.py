# from modbus.client import client
import serial
import time


def run_sync_client():
    ser = serial.Serial('COM1', 9600, timeout=0.3,  stopbits=1)
    mes = str.encode('#011\r')      # \r - добавляет (cr) как в документации ADAM
    ser.write(mes)
    # print(len(mes), type(mes))
    data = ser.readall()
    data = int(str(data[2:7].decode()).replace('.', ''))

    print('ADAM:', data/1000, 'V')


ipadr = 'localhost'
ipadr = '192.168.110.2'
ipadr = '10.10.88.19'

# c = client(host=ipadr)
# data = 0

if __name__ == '__main__':
    while True:
        # time.sleep(1)
        run_sync_client()

        # r = c.read(FC=4, ADR=998, LEN=1)
        # # w = c.write(FC=16, ADR=998, DAT=12)
        # c.write(FC=16, ADR=998, dat=data)
        # data = data + 3
        # print('PLC_mw998: ', r[0])

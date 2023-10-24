"""
опрос модуля дискретного ввода/вывода ПИ 485-32D по модбас рту
"""
import serial
import struct
import time

def open_com(port='COM2'):
    try:
        ser = serial.Serial(port=port, baudrate=19200, timeout=1, bytesize=serial.EIGHTBITS, stopbits=1)
    except serial.SerialException:
        print(f"could not open {port}")
        time.sleep(1) 
    else:
        return ser    # если удалось открыть com порт

def request()  -> None:
    ser = open_com()
    if ser:
        # стандартный запрос регистров ввода в 16-ричном формате modbus rtu (01 04 0000 0012 7007)
        # 01 = адрес, 
        # 04 - регистры ввода
        # 0000 - стартовый адрес, 
        # 0012 - 18 значений, контрольная сумма crc16 modbus переворачивается
        # 7007 crc - https://crccalc.com/ - расчет crc)
        request = bytes.fromhex('02 04 0000 0001 31F9')
        ser.write(request)

def response(ser):
    if ser:
        data = ser.readall()
        print('data', data)


if __name__ == '__main__':
    while True:
        request()
        response(open_com())
        # print(time.ctime())        # делим на 10 в описании так сказано
"""
опрос радиометра загрязненности РЗБА-04-04М по модбас рту
подключение ноут -> мокса ->(два провода) разьем-1 (их там два) -> нельзя считать отдельный регистр, только массив
19 т.к. Float занимает 2 регистра - длина массива общих параметров (ТАБЛИЦА 1 из протокола обмена )
"""

import serial
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
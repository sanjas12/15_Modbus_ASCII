"""
опрос радиометра загрязненности РЗБА-04-04М по модбас рту
подключение ноут -> мокса ->(два провода) разьем-1 (их там два) -> нельзя считать отдельный регистр, только массив
19 т.к. Float занимает 2 регистра - длина массива общих параметров (ТАБЛИЦА 1 из протокола обмена )

'02 03 0000 0019 3384' - со 2 адреса, 03-функция считывания, с 0000 - регистра, 19 - регистров.
"""

import serial
import time

def open_com(port='COM2'):
    try:
        ser = serial.Serial(port=port, baudrate=9600, timeout=1, bytesize=serial.EIGHTBITS, stopbits=1)
    except serial.SerialException:
        print(f"could not open {port}")
        time.sleep(1) 
    else:
        return ser    # если удалось открыть com порт

def request()  -> None:
    ser = open_com()
    if ser:
        request = bytes.fromhex('02 03 0000 0019 3384')
        ser.write(request)

def response(ser):
    if ser:
        data = ser.readall()
        print('data', data)


if __name__ == '__main__':
    while True:
        request()
        response(open_com())
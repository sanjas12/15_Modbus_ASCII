"""
опрос модуля дискретного ввода/вывода ПИ 485-32D по модбас рту
"""
import serial
import struct
import time


def request()  -> None:
    ser = serial.Serial('COM2', 19200, timeout=1, bytesize=serial.EIGHTBITS, stopbits=1)

    # стандартный запрос регистров ввода в 16-ричном формате modbus rtu (01 04 0000 0012 7007)
    # 01 = адрес, 
    # 04 - регистры ввода
    # 0000 - стартовый адрес, 
    # 0012 - 18 значений, контрольная сумма crc16 modbus переворачивается
    # 7007 crc - https://crccalc.com/ - расчет crc)
    if ser.isOpen(): 
        request = bytes.fromhex('02 04 0000 0001 31F9')
        ser.write(request)

    data = ser.readall()  # ответ в байтах

def all_response(data: bytes):

    temperature = data[12]/10
    print('Teмпература:', temperature)

    # print(data[3:7].hex('.'))     # convert byte to hex

    high_word = bytearray(data[3:5])
    high_word.reverse()
    low_word = bytearray(data[5:7])
    low_word.reverse()
    torque = struct.unpack('f', high_word+low_word)[0]
    print('Крутящий момент:', torque)


if __name__ == '__main__':
    while True:
        response = request()        # делим на 10 в описании так сказано
        print(time.ctime(), repr(response))        # делим на 10 в описании так сказано
"""
опрос модуля дискретного ввода/вывода ПИ 485-32D по модбас рту
"""
import serial
import struct


def request():
    ser = serial.Serial('COM2', 19200, timeout=1, bytesize=serial.EIGHTBITS, stopbits=1)

    # стандартный запрос регистров ввода в 16-ричном формате modbus rtu (01 04 0000 0012 7007)
    # 01 = адрес, 
    # 04 - регистры ввода
    # 0000 - стартовый адрес, 
    # 0012 - 18 значений, контрольная сумма crc16 modbus переворачивается
    # 7007 crc - https://crccalc.com/ - расчет crc)

    # запрос всех  значений
    request = bytes.fromhex('02 04 0000 0001 31F9')

    # только температура
    # request = bytes.fromhex('01 04 0004 0001 700B')

    # только момент
    # request = bytes.fromhex('01 04 0000 0002 701A')

    ser.write(request)
    data = ser.readall()  # ответ в байтах

    # ответ на 01 04 0000 0012 7007
    # b'\x01\x04$~P\xbc\xa7\x00\x00\x00\x00\x00d\x00\x05\x00\x00\x00\x05\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1f\xbe\xe6'
    # b = b'\x01\x04$~P\xbc\xa7\x00\x00\x00\x00\x00d\x00\x05\x00\x00\x00\x05\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1f\xbe\xe6'
    # в формате сервер клиента
    # 01.04.24.F6.69.BC.B1.00.00.00.00.00.64.00.05.00.00.00.05.00.02.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.1F.35.69.
    # 01.04.24.A0.2C.BC.E2.00.00.00.00.00.5F.00.05.00.04.00.05.00.02.00.01.00.08.00.00.00.00.00.00.00.00.00.00.00.00.00.1F.84.DA.

    # print(type(data))
    # print(type(bytes.hex(data, '.'))) # вывод байт в hex

    # ответ на запрос температуры 01.04.02.00.64.B8.DB. (01 - адрес 04- регистры ввода 02 колическво байт знаяений,
    # 00.64 - данные значений, b8 d8 - crc так же перевернут)(7байт) температура идет 5 байтом
    # print(data[4])

    return data


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

    # file = 'torque'
    # with open(file, 'a') as f:
    #     f.write(data[3:7].hex('.')+'\n')


if __name__ == '__main__':
    while True:
        response = request()        # делим на 10 в описании так сказано
        # if len(response) == 7:
        #     temprature = request()[4] / 10  # делим на 10 в описании так сказано
        #     print('Температура:', temprature)
        # else:
        #     all_response(response)
        print(response)        # делим на 10 в описании так сказано
)
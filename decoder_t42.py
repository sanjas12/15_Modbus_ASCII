import serial


def run_sync_client():
    ser = serial.Serial('COM27', 115200, timeout=1, bytesize=serial.EIGHTBITS,
                        stopbits=1)

    # запрос документации минских чуваков

    request = bytes.fromhex('00 04 0000 0002 701A')
    request = bytes.fromhex('00 04 0000 0200 701A')

    print(request)

    ser.write(request)
    # print(len(mes), type(mes))
    data = ser.readall()
    # data = int(str(data[2:7].decode()).replace('.', ''))




    # print('T42:', data/1000, 'V')

    print(data)
    return data


if __name__ == '__main__':
    while True:
        run_sync_client()
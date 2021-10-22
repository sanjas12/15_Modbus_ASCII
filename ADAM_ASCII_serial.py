import serial


def run_sync_client():
    ser = serial.Serial('COM1', 9600, timeout=0.3,  stopbits=1)
    mes = str.encode('#011\r')      # \r - добавляет (cr) как в документации ADAM
    ser.write(mes)
    # print(len(mes), type(mes))
    data = ser.readall()
    data = int(str(data[2:7].decode()).replace('.', ''))

    print('ADAM:', data/1000, 'V')

    return data


if __name__ == '__main__':
    while True:
        run_sync_client()


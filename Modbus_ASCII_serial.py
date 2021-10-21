import serial


def run_sync_client():
    ser = serial.Serial('COM1', 9600, timeout=0.1,  stopbits=1)
    mes = str.encode('#010\r')      # \r - добавляет (cr) как в документации ADAM
    ser.write(mes)
    print(ser.readall())


if __name__ == '__main__':
    while True:
        run_sync_client()

import serial
import time


class Serial():
    def __init__(self, port='COM1', baudrate=9600, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=0.001):
        self.s = serial.Serial(timeout=timeout)
        self.s.port = port
        self.s.baudrate = baudrate
        self.s.parity = parity
        self.s.stopbits = stopbits
        self.port = port
        self.slave_id = 0
        self.function = 0
        self.cmd = 0
        self.start_addr = 0
        self.quantity = 0
        self.value = 0
        self.byte_count = 0
        self.dst = 0
        self.src = 0
        self.buffer = ''

    def receive_data(self):
        size = self.s.inWaiting()
        if size:
            self.buffer += self.s.read_all()
        return size

    def read_data_with_slip(self):
        data = ''
        try:
            # self.s.read() ??? first 0xC0 byte?
            while 1:
                b = self.s.read()
                if len(b) == 0:
                    break
                # if unpack('B', b)[0] == 0xC0:
                if b[0] == chr(0xC0):
                    return data
                # print(len(b))
                # if len(b) > 0:
                # pass
                # if len(b) > 0 and b[0] == chr(0xC0):
                # return data

                data += b
            # sleep(0.001)
        except serial.SerialException as e:
            # print e
            pass
        # self.buffer = ''
        # try:
        #     while 1:
        #         if self.receive_data():
        #             if self.buffer[-1] == '\xc0':
        #                 return self.buffer[:-1]
        #         sleep(0.001)
        # except serial.SerialException, e:
        #     # print e
        #     pass

    def parsing_data(self):
        if self.buffer[0] == 1:
            # modbus RTU
            pass
        elif self.buffer[0] == '0x1f':
            # sensors
            # find end of statement '0x2f'
            pass
        elif self.buffer[0] == '0xc0':
            # valves, lsu
            # find end of statement '0xc0'
            pass

    def connect(self):
        try:
            self.s.open()
        except serial.SerialException:
            # print 'could not open port %s' % self.port
            self.disconnect()
            time.sleep(1)
        except WindowsError:
            pass
        else:
            self.s.reset_input_buffer()
            self.s.reset_output_buffer()
            print('port %s opened' % self.port)

    def disconnect(self):
        if self.s.is_open:
            self.s.close()
            print('port %s closed' % self.port)

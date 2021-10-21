import minimalmodbus
import time


# port name, slave address (in decimal)
instrument = minimalmodbus.Instrument('COM1', 1, minimalmodbus.MODE_ASCII,  debug=True)
instrument.serial.baudrate = 9600 # Baud
instrument.serial.bytesize = 8
instrument.serial.parity = 'N'
instrument.serial.stopbits = 1
instrument.serial.timeout = 0.05 # seconds
instrument.close_port_after_each_call = True

# print(instrument)
# time.sleep(1)
# mes = str.encode('$01M')
# mes = '$01M'
# print(mes)
# ## Read temperature (PV = ProcessValue) ##
# instrument.write_string(textstring=mes, registeraddress=1)
# print(instrument.read_string(1024))
# print(temperature)
r = instrument.read_register(1, functioncode=3)
# instrument.serial.close()
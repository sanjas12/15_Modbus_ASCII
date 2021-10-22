import Modbus_ASCII_serial
import PLC

while True:
    adam = [Modbus_ASCII_serial.run_sync_client()]
    PLC.plc(list(adam))

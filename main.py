import Modbus_ASCII_serial
import PLC

while True:
    adam = [Modbus_ASCII_serial.run_sync_client()]
    # adam = [adam]
    # print(type(adam), adam, len(adam))
    PLC.plc(list(adam))
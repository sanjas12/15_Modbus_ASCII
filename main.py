import ADAM_ASCII_serial
import PLC

while True:
    print('*'*20)
    adam = [ADAM_ASCII_serial.run_sync_client()]
    PLC.plc(list(adam))

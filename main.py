import modbus_tcp.ADAM_4017 as ADAM_4017
import modbus_tcp.PLC as PLC

while True:
    print('*'*20)
    adam = [ADAM_4017.run_sync_client()]
    PLC.plc(list(adam))

import ADAM_4017
import PLC

while True:
    print('*'*20)
    adam = [ADAM_4017.run_sync_client()]
    PLC.plc(list(adam))

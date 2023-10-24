from pyModbusTCP.client import ModbusClient
import time

SERVER_HOST = "192.168.30.11"

cl = ModbusClient(host=SERVER_HOST)


def dec_to_ma(dec):
    ValMax, ValMin = 20.0, 4.0
    Amax, Amin = 65535,  0.0
    shift = 0.0 
    ma = ((ValMax-ValMin)*(dec-Amin))/(Amax-Amin) + (ValMin + shift) 
    return ma

def adam_6017():
    data_read = cl.read_holding_registers(1, 8)     # 1 - соответствует адресу 40001  по ADAM-6000_User_Manaul_Ed.10-FINAL.pdf
                                                    #  стр. 217
    print(f'data from ADAM_6017 ch_0:  {data_read[0]}, {round(dec_to_ma(data_read[0]), 2)} mA')
    time.sleep(0.1)


if __name__ == '__main__':
    while True:
        adam_6017()

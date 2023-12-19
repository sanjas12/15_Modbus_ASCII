pip install pyserial-3.5-py2.py3-none-any.whl - установка через pip

ADAM_4017.py - рабочая версия соединения с ADAM-4017 (ASCII_serial) через MOXU 1150i и два провода

PLC.py - соединение с PLC m580

test - это реализация Modbus_ASCII в ЛСУ

indicator_t42.py - обмен с индикатором Т42 для дока

<!-- стандартный запрос регистров ввода в 16-ричном формате modbus rtu (02 04 0000 0001 31F9) -->
02 - адрес устройства
04 - функция считывания (04 - регистры ввода)
0000 - начальный (стартовый) регистр 
0001 - кол-во регистров
31F9 - CRC

https://crccalc.com/ - расчет crc  CRC-16/MODBUS


<!-- стандартный запрос modbus tcp (02 04 0000 0001 31F9) -->
https://ipc2u.com/articles/knowledge-base/detailed-description-of-the-modbus-tcp-protocol-with-command-examples/

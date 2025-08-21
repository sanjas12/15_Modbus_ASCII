import sys
from typing import List, Optional

from PyQt5 import QtCore, QtWidgets

from modbus_client import ModbusClientWrapper
from telemetry import decode_SW1, decode_SW2
from signals import Signals


class WorkerSignals(QtCore.QObject):
    result = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)


class Runnable(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))


class VFDModbusWindow(QtWidgets.QMainWindow):
    """
    Главное окно приложения для работы с RI-350 через Modbus TCP.
    Управляет UI, обработкой команд, логированием и асинхронными задачами.
    """
    # Константы адресов регистров RI-350
    REG_CMD = 0x2000
    REG_FREQ_SET = 0x2001
    REG_PID_SET = 0x2002
    REG_STATE1 = 0x2100
    REG_STATE2 = 0x2101
    REG_FREQ_READ = 0x3000

    DEVICE = "RI350"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RI-350-19")

        self.modbus = ModbusClientWrapper()
        self.thread_pool = QtCore.QThreadPool.globalInstance()

        # --- UI controls (инициализируем в __init__ для стат. анализа) ---
        # Connection
        self.edit_ip = QtWidgets.QLineEdit("192.168.0.20")
        self.spin_port = QtWidgets.QSpinBox()
        self.spin_unit = QtWidgets.QSpinBox()
        self.btn_connect = QtWidgets.QPushButton("Подключиться")
        self.btn_disconnect = QtWidgets.QPushButton("Отключиться")
        self.lbl_status = QtWidgets.QLabel("Отключено")

        # Log
        self.text_log = QtWidgets.QPlainTextEdit()

        # Read tab controls (сейчас вкладка выключена — оставляем для будущего)
        self.combo_read_func = QtWidgets.QComboBox()
        self.spin_read_address = QtWidgets.QSpinBox()
        self.spin_read_quantity = QtWidgets.QSpinBox()
        self.btn_read = QtWidgets.QPushButton("Читать")
        self.table_read = QtWidgets.QTableWidget(0, 2)

        # Write tab controls
        self.combo_write_func = QtWidgets.QComboBox()
        self.spin_write_address = QtWidgets.QSpinBox()
        self.edit_values = QtWidgets.QLineEdit()
        self.btn_write = QtWidgets.QPushButton("Записать")

        # RI350 commands
        self.btn_cmd_fwd = QtWidgets.QPushButton("Вперед")
        self.btn_cmd_rev = QtWidgets.QPushButton("Назад")
        self.btn_cmd_jog_fwd = QtWidgets.QPushButton("Толчок вперед")
        self.btn_cmd_jog_rev = QtWidgets.QPushButton("Толчок назад")
        self.btn_cmd_stop = QtWidgets.QPushButton("Стоп")
        self.btn_cmd_estop = QtWidgets.QPushButton("Аварийный останов")
        self.btn_cmd_reset = QtWidgets.QPushButton("Сброс ошибки")
        self.btn_cmd_jog_to_stop = QtWidgets.QPushButton("Толчок для останова")

        # Telemetry labels first column
        self.lbl_tel_state1 = QtWidgets.QLabel("—")
        self.lbl_tel_state1_raw = QtWidgets.QLabel("—")
        self.lbl_tel_ready = QtWidgets.QLabel("—")
        self.lbl_tel_motor_sel = QtWidgets.QLabel("—")
        self.lbl_tel_motor_type = QtWidgets.QLabel("—")
        self.lbl_tel_overload = QtWidgets.QLabel("—")
        self.lbl_tel_ctrl_src = QtWidgets.QLabel("—")
        self.lbl_tel_mode = QtWidgets.QLabel("—")
        self.lbl_tel_position = QtWidgets.QLabel("—")
        self.lbl_tel_vector = QtWidgets.QLabel("—")
        self.lbl_tel_state2_raw = QtWidgets.QLabel("—")
        
        # Telemetry labels second column
        self.lbl_tel_cur_freq = QtWidgets.QLabel("—")   #0
        self.lbl_tel_aim_freq = QtWidgets.QLabel("—")
        self.lbl_tel_volt_DC = QtWidgets.QLabel("—")
        self.lbl_tel_out_volt = QtWidgets.QLabel("—")
        self.lbl_tel_out_cur = QtWidgets.QLabel("—")
        self.lbl_tel_velocity = QtWidgets.QLabel("—")     #5
        self.lbl_tel_out_power = QtWidgets.QLabel("—")
        self.lbl_tel_out_torq = QtWidgets.QLabel("—")
        self.lbl_tel_out_close_loop = QtWidgets.QLabel("—")
        self.lbl_tel_out_close_loop_feedback = QtWidgets.QLabel("—")
        self.lbl_tel_input_state = QtWidgets.QLabel("—")
        self.lbl_tel_output_state = QtWidgets.QLabel("—")
        self.lbl_tel_analog_input_1 = QtWidgets.QLabel("—")
        self.lbl_tel_analog_input_2 = QtWidgets.QLabel("—")
        self.lbl_tel_analog_input_3 = QtWidgets.QLabel("—")
        self.lbl_tel_analog_input_4 = QtWidgets.QLabel("—")
        self.lbl_tel_read_input_of_HDIA = QtWidgets.QLabel("—") # 16
        self.lbl_tel_read_input_of_HDIB = QtWidgets.QLabel("—")
        self.lbl_tel_read_current_step = QtWidgets.QLabel("—")
        self.lbl_tel_external_length = QtWidgets.QLabel("—")
        self.lbl_tel_external_count_value = QtWidgets.QLabel("—")
        self.lbl_tel_torq_setting = QtWidgets.QLabel("—")
        self.lbl_tel_id_code = QtWidgets.QLabel("—")
        
        
        self.lbl_tel_fault_code = QtWidgets.QLabel("—")
        
        self.btn_refresh_tel = QtWidgets.QPushButton("Обновить")
        self.chk_tel_auto = QtWidgets.QCheckBox("Автообновление")
        self.spin_tel_period = QtWidgets.QSpinBox()
        self.spin_tel_period.setRange(100, 10000)
        self.spin_tel_period.setSingleStep(100)
        self.spin_tel_period.setValue(100)

        # Auto-refresh runtime
        self.telemetry_timer = QtCore.QTimer(self)

        self._connected: bool = False
        self._tel_busy: bool = False

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        # Главный контейнер: горизонтально (слева UI, справа журнал)
        layout_main = QtWidgets.QHBoxLayout()
        central.setLayout(layout_main)

        layout_left = QtWidgets.QVBoxLayout()
        layout_middle = QtWidgets.QVBoxLayout()
        layout_right = QtWidgets.QVBoxLayout()

        # --- Connection box ---
        conn_box = QtWidgets.QGroupBox("Подключение")
        conn_layout = QtWidgets.QGridLayout(conn_box)

        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(502)
        self.spin_unit.setRange(0, 255)
        self.spin_unit.setValue(1)

        self.lbl_status.setStyleSheet("color: #a00;")

        conn_layout.addWidget(QtWidgets.QLabel("IP"), 0, 0)
        conn_layout.addWidget(self.edit_ip, 0, 1)
        conn_layout.addWidget(QtWidgets.QLabel("Порт"), 0, 2)
        conn_layout.addWidget(self.spin_port, 0, 3)
        conn_layout.addWidget(QtWidgets.QLabel("Unit ID"), 0, 4)
        conn_layout.addWidget(self.spin_unit, 0, 5)
        conn_layout.addWidget(self.btn_connect, 1, 1)
        conn_layout.addWidget(self.btn_disconnect, 1, 2)
        conn_layout.addWidget(QtWidgets.QLabel("Состояние:"), 1, 4)
        conn_layout.addWidget(self.lbl_status, 1, 5)

        # --- Tabs ---
        tabs = QtWidgets.QTabWidget()
        # tabs.addTab(self._build_read_tab(), "Чтение")
        # tabs.addTab(self._build_write_tab(), "Запись")
        tabs.addTab(self._build_ri350_tab(), "RI350")

        # --- Log box ---
        log_box = QtWidgets.QGroupBox("Журнал")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        self.text_log.setReadOnly(True)
        self.text_log.setMinimumHeight(400)
        self.text_log.setMinimumWidth(600)
        log_layout.addWidget(self.text_log)

        layout_left.addWidget(conn_box)
        layout_left.addWidget(tabs)
        
        layout_middle.addWidget(self._build_telemetry_group())

        layout_right.addWidget(log_box)

        layout_main.addLayout(layout_left)
        layout_main.addLayout(layout_middle)
        layout_main.addLayout(layout_right)

    def _build_read_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)

        self.combo_read_func.addItems(
            [
                "Holding Registers (0x03)",
                "Input Registers (0x04)",
                "Coils (0x01)",
                "Discrete Inputs (0x02)",
            ]
        )
        self.spin_read_address.setRange(0, 65535)
        self.spin_read_quantity.setRange(1, 125)
        self.spin_read_quantity.setValue(1)

        self.table_read.setHorizontalHeaderLabels(["Адрес", "Значение"])
        self.table_read.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(QtWidgets.QLabel("Функция"), 0, 0)
        layout.addWidget(self.combo_read_func, 0, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel("Адрес"), 1, 0)
        layout.addWidget(self.spin_read_address, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Количество"), 1, 2)
        layout.addWidget(self.spin_read_quantity, 1, 3)
        layout.addWidget(self.btn_read, 1, 4)
        layout.addWidget(self.table_read, 2, 0, 1, 5)
        return page

    def _build_write_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)

        self.combo_write_func.addItems(
            [
                "Single Register (0x06)",
                "Multiple Registers (0x10)",
                "Single Coil (0x05)",
                "Multiple Coils (0x0F)",
            ]
        )
        self.spin_write_address.setRange(0, 65535)
        self.edit_values.setPlaceholderText(
            "значения через запятую, напр.: 100,200,300 или true,false"
        )

        layout.addWidget(QtWidgets.QLabel("Функция"), 0, 0)
        layout.addWidget(self.combo_write_func, 0, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel("Адрес"), 1, 0)
        layout.addWidget(self.spin_write_address, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Значения"), 1, 2)
        layout.addWidget(self.edit_values, 1, 3, 1, 2)
        layout.addWidget(self.btn_write, 1, 5)
        return page

    def _wire_signals(self) -> None:
        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_disconnect.clicked.connect(self.on_disconnect)

        self.btn_read.clicked.connect(self.on_read)
        self.btn_write.clicked.connect(self.on_write)

        # RI350
        self.btn_cmd_fwd.clicked.connect(
            lambda: self.comand_to_control_motor(0x0001, "Вперед")
        )
        self.btn_cmd_rev.clicked.connect(
            lambda: self.comand_to_control_motor(0x0002, "Назад")
        )
        self.btn_cmd_jog_fwd.clicked.connect(
            lambda: self.comand_to_control_motor(0x0003, "Толчок вперед")
        )
        self.btn_cmd_jog_rev.clicked.connect(
            lambda: self.comand_to_control_motor(0x0004, "Толчок назад")
        )
        self.btn_cmd_stop.clicked.connect(
            lambda: self.comand_to_control_motor(0x0005, "Стоп")
        )
        self.btn_cmd_estop.clicked.connect(
            lambda: self.comand_to_control_motor(0x0006, "Аварийный останов")
        )
        self.btn_cmd_reset.clicked.connect(
            lambda: self.comand_to_control_motor(0x0007, "Сброс ошибки")
        )
        self.btn_cmd_jog_to_stop.clicked.connect(
            lambda: self.comand_to_control_motor(0x0008, "Толчок для останова")
        )

        # Telemetry
        self.btn_refresh_tel.clicked.connect(self.on_refresh_telemetry)
        self.telemetry_timer.timeout.connect(self.on_refresh_telemetry)
        self.chk_tel_auto.toggled.connect(lambda _checked: self._start_telemetry_timer())
        self.spin_tel_period.valueChanged.connect(
            lambda _v: self._start_telemetry_timer()
        )

    def _build_ri350_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)
        
        # Команды управления
        layout.addWidget(
            QtWidgets.QLabel("Команды управления (регистр 0x2000)"), 0, 0, 1, 2
        )
        layout.addWidget(self.btn_cmd_fwd, 1, 0)
        layout.addWidget(self.btn_cmd_rev, 1, 1)
        layout.addWidget(self.btn_cmd_jog_fwd, 2, 0)
        layout.addWidget(self.btn_cmd_jog_rev, 2, 1)
        layout.addWidget(self.btn_cmd_stop, 3, 0)
        layout.addWidget(self.btn_cmd_estop, 3, 1)
        layout.addWidget(self.btn_cmd_reset, 4, 0)
        layout.addWidget(self.btn_cmd_jog_to_stop, 4, 1)

       
        com_setting_box = QtWidgets.QGroupBox("Communication RW settings ")
        com_setting_layout = QtWidgets.QGridLayout(com_setting_box)
        
        self.signals = Signals()

        for row, (name, parameter) in enumerate(self.signals.parameters.items()):
            com_setting_layout.addWidget(QtWidgets.QLabel(name), row, 0)
            
            com_setting_layout.addWidget(parameter.spin_box, row, 1)
            parameter.spin_box.setValue(parameter.default_value)
            parameter.spin_box.setSingleStep(parameter.single_step)
            parameter.spin_box.setRange(*parameter.range)
            
            com_setting_layout.addWidget(parameter.btn_set, row, 2)
            parameter.btn_set.clicked.connect(lambda: self.set_register_value(parameter.spin_box, parameter.modbus_address, 1, name))
        
        # row = 0
        self.spin_test = QtWidgets.QSpinBox()
        self.spin_test.setValue(0)
        self.spin_test.setSingleStep(1)
        self.spin_test.setRange(0,15)
        self.btn_test = QtWidgets.QPushButton("Задать входы")
        com_setting_layout.addWidget(self.btn_test, row+1, 2)
        com_setting_layout.addWidget(self.spin_test, row+1, 1)
        self.btn_test.clicked.connect(lambda: self.test(self.spin_test.value(), "Test"))
        layout.addWidget(com_setting_box, row, 0, 1, 2)

        return page

    def test(self, code: int, title: str) -> None:
        address = 0x200A

        def after(ok: bool) -> None:
            self.log(
                f"RI350: {title} → регистр 0x{address:04X} значение 0x{code:04X} — "
                f"{'OK' if ok else 'ОШИБКА'}"
            )
        if self.modbus.is_connected():
            self._submit(self.modbus.write_single_register, after, address, int(code))
        else:
            self.show_error(f"RI350: Задать DI входы → {self.modbus.NOT_CONNECT}")

    def comand_to_control_motor(self, code: int, title: str) -> None:
        address = 0x2000

        def after(ok: bool) -> None:
            self.log(
                f"RI350: {title} → регистр 0x{address:04X} значение 0x{code:04X} — "
                f"{'OK' if ok else 'ОШИБКА'}"
            )

        self._submit(self.modbus.write_single_register, after, address, int(code))

    # --- Telemetry (address_R) ---
    def _build_telemetry_group(self) -> QtWidgets.QGroupBox:
        page = QtWidgets.QGroupBox("Телеметрия")
        layout = QtWidgets.QGridLayout(page)

        r = 0
        layout.addWidget(QtWidgets.QLabel("ПЧ слово состояния 1 (0x2100)"), r, 0, 1, 2)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Состояние"), r, 0)
        layout.addWidget(self.lbl_tel_state1, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("RAW"), r, 0)
        layout.addWidget(self.lbl_tel_state1_raw, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("ПЧ слово состояния 2 (0x2101)"), r, 0, 1, 2)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Готов к запуску"), r, 0)
        layout.addWidget(self.lbl_tel_ready, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Выбран двигатель"), r, 0)
        layout.addWidget(self.lbl_tel_motor_sel, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Тип двигателя"), r, 0)
        layout.addWidget(self.lbl_tel_motor_type, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Авария перегрузки"), r, 0)
        layout.addWidget(self.lbl_tel_overload, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Источник управления"), r, 0)
        layout.addWidget(self.lbl_tel_ctrl_src, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Режим управления"), r, 0)
        layout.addWidget(self.lbl_tel_mode, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Позиционное управление"), r, 0)
        layout.addWidget(self.lbl_tel_position, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("Тип вектора"), r, 0)
        layout.addWidget(self.lbl_tel_vector, r, 1)
        r += 1
        layout.addWidget(QtWidgets.QLabel("RAW"), r, 0)
        layout.addWidget(self.lbl_tel_state2_raw, r, 1)
        r += 1


        # Параллельная колонка с текущей частотой (справа сверху)
        r=0
        layout.addWidget(QtWidgets.QLabel("Рабочая частота, Гц"), r, 2)
        layout.addWidget(self.lbl_tel_cur_freq, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Заданная частота, Гц"), r, 2)
        layout.addWidget(self.lbl_tel_aim_freq, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Напряжение DC-шины"), r, 2)
        layout.addWidget(self.lbl_tel_volt_DC, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Выходное напряжение"), r, 2)
        layout.addWidget(self.lbl_tel_out_volt, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Выходной ток"), r, 2)
        layout.addWidget(self.lbl_tel_out_cur, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Скорость вращения, об/мин"), r, 2)
        layout.addWidget(self.lbl_tel_velocity, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Выходная мощность"), r, 2)
        layout.addWidget(self.lbl_tel_out_power, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Выходная момент"), r, 2)
        layout.addWidget(self.lbl_tel_out_torq, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Настройка замкнутого контура"), r, 2)
        layout.addWidget(self.lbl_tel_out_close_loop, r, 3)
        r+=1
        
        layout.addWidget(QtWidgets.QLabel("Обратная связь с замкнутым контуром"), r, 2)
        layout.addWidget(self.lbl_tel_out_close_loop_feedback, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Состояние входов"), r, 2)
        layout.addWidget(self.lbl_tel_input_state, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Состояние выходов"), r, 2)
        layout.addWidget(self.lbl_tel_output_state, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Аналоговый вход 1"), r, 2)
        layout.addWidget(self.lbl_tel_analog_input_1, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Аналоговый вход 2"), r, 2)
        layout.addWidget(self.lbl_tel_analog_input_2, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Аналоговый вход 3"), r, 2)
        layout.addWidget(self.lbl_tel_analog_input_3, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Аналоговый вход 4"), r, 2)
        layout.addWidget(self.lbl_tel_analog_input_4, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Считывание сигнала высокоскоростного импульсного входа HDIA"), r, 2)
        layout.addWidget(self.lbl_tel_read_input_of_HDIA, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Считывание сигнала высокоскоростного импульсного входа HDIB"), r, 2)
        layout.addWidget(self.lbl_tel_read_input_of_HDIB, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Считывание текущего шага многоступенчатой скорости"), r, 2)
        layout.addWidget(self.lbl_tel_read_current_step, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Внешняя длина"), r, 2)
        layout.addWidget(self.lbl_tel_external_length, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Значение внешнего счетчика"), r, 2)
        layout.addWidget(self.lbl_tel_external_count_value, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Задание крутящего момента"), r, 2)
        layout.addWidget(self.lbl_tel_torq_setting, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Идентификационный код"), r, 2)
        layout.addWidget(self.lbl_tel_id_code, r, 3)
        r+=1

        layout.addWidget(QtWidgets.QLabel("Код ошибки"), r, 2)
        layout.addWidget(self.lbl_tel_fault_code, r, 3)
        r+=1

        layout.addWidget(self.btn_refresh_tel, r, 0)
        layout.addWidget(self.chk_tel_auto, r, 1)
        layout.addWidget(QtWidgets.QLabel("Период, мс"), r, 2)
        layout.addWidget(self.spin_tel_period, r, 3)

        return page

    def on_refresh_telemetry(self) -> None:
        # print("on_refresh_telemetry")
        if self._tel_busy:
            return
        self._tel_busy = True

        # Читаем 0x2100 (SW1) → 0x2101(SW2) → 0x3000(16 байт) -> отстальный 11 ->  по цепочке
        def finish():
            # Сбрасываем флаг в конце любой ветки
            self._tel_busy = False

        def fault_code(data: Optional[List[int]]) -> None:
            # adress = 0x5000
            self.lbl_tel_fault_code.setText(f"{(data or 0) if data is not None else None}")
            finish()

        def after_SWs_first_16(data: Optional[List[int]]) -> None:
            """разбираем массив данных из ПЧ"""
            try:
                if data:
                    hz = (data[0] or 0) / 100.0
                    self.lbl_tel_cur_freq.setText(f"{hz:.2f}")
                    aim_hz = (data[1] or 0) / 100.0 if data[1] is not None else None
                    self.lbl_tel_aim_freq.setText(f"{aim_hz:.2f}")
                    self.lbl_tel_volt_DC.setText(f"{(data[2] or 0) if data[2] is not None else None}")
                    self.lbl_tel_out_volt.setText(f"{(data[3] or 0) if data[3] is not None else None}")
                    self.lbl_tel_out_cur.setText(f"{(data[4] or 0) if data[4] is not None else None}")
                    velocity = (data[5] or 0) if data[5] is not None else None
                    self.lbl_tel_velocity.setText(f"{velocity:.2f}")
                    self.lbl_tel_out_power.setText(f"{(data[6] or 0) if data[6] is not None else None}")
                    self.lbl_tel_out_torq.setText(f"{(data[7] or 0) if data[7] is not None else None}")
                    self.lbl_tel_out_close_loop.setText(f"{(data[8] or 0) if data[8] is not None else None}")
                    self.lbl_tel_out_close_loop_feedback.setText(f"{(data[9] or 0) if data[9] is not None else None}")
                    self.lbl_tel_input_state.setText(f"{(data[10] or 0) if data[10] is not None else None}")
                    self.lbl_tel_output_state.setText(f"{(data[11] or 0) if data[11] is not None else None}")
                    self.lbl_tel_analog_input_1.setText(f"{(data[12] or 0) if data[12] is not None else None}")
                    self.lbl_tel_analog_input_2.setText(f"{(data[13] or 0) if data[13] is not None else None}")
                    self.lbl_tel_analog_input_3.setText(f"{(data[14] or 0) if data[14] is not None else None}")
                    self.lbl_tel_analog_input_4.setText(f"{(data[15] or 0) if data[15] is not None else None}")
                else:
                    self.lbl_tel_cur_freq.setText("—")
                    self.lbl_tel_aim_freq.setText("-")
                    self.lbl_tel_volt_DC.setText("-")
                    self.lbl_tel_out_volt.setText("-")
                    self.lbl_tel_out_cur.setText("-")
                    self.lbl_tel_velocity.setText("-")
                    self.lbl_tel_out_power.setText("-")
                    self.lbl_tel_out_torq.setText("-")
                    self.lbl_tel_out_close_loop.setText("-")
                    self.lbl_tel_out_close_loop_feedback.setText("-")
                    self.lbl_tel_input_state.setText("-")
                    self.lbl_tel_output_state.setText("-")
                    self.lbl_tel_analog_input_1.setText("-")
                    self.lbl_tel_analog_input_2.setText("-")
                    self.lbl_tel_analog_input_3.setText("-")
                    self.lbl_tel_analog_input_4.setText("-")
            finally:
                self._submit(self.modbus.read_holding, after_SWs_second_16, 0x300A, 7)  # удавалось считывать 16 адресов максимум

        def after_SWs_second_16(data: Optional[List[int]]) -> None:
            # print(f"after_Safter_SWs_second_16  {data=}")
            """разбираем массив данных из ПЧ"""
            if data:
                self.lbl_tel_read_input_of_HDIA.setText(f"{(data[0] or 0) if data[0] is not None else None}")
                self.lbl_tel_read_input_of_HDIB.setText(f"{(data[1] or 0) if data[1] is not None else None}")
                self.lbl_tel_read_current_step.setText(f"{(data[2] or 0) if data[2] is not None else None}")
                self.lbl_tel_out_close_loop.setText(f"{ (data[3] or 0) if data[3] is not None else None}")
                self.lbl_tel_out_close_loop_feedback.setText(f"{(data[4] or 0) if data[4] is not None else None}")
                self.lbl_tel_torq_setting.setText(f"{(data[5] or 0) if data[5] is not None else None}")
                self.lbl_tel_id_code.setText(f"{(data[6] or 0) if data[6] is not None else None}")
            else:
                self.lbl_tel_read_input_of_HDIA.setText("-")
                self.lbl_tel_read_input_of_HDIB.setText("-")
                self.lbl_tel_read_current_step.setText("-")
                self.lbl_tel_external_length.setText("-")
                self.lbl_tel_external_count_value.setText("-")
                self.lbl_tel_torq_setting.setText("-")
                self.lbl_tel_id_code.setText("-")
            
            self._submit(self.modbus.read_holding, fault_code, 0x5000, 1)

        def read_cw(data: Optional[List[int]]) -> None:
            cw1 = data[0] if data and len(data) > 0 else None
            cw2 = data[1] if data and len(data) > 0 else None
            
            if cw1 is not None:
                self.lbl_tel_state1.setText(decode_SW1(int(cw1)))
                self.lbl_tel_state1_raw.setText(f"0x{int(cw1):04X}")
            else:
                self.lbl_tel_state1.setText("—")
                self.lbl_tel_state1_raw.setText("—")

            if cw2 is not None:
                self.lbl_tel_state2_raw.setText(f"0x{int(cw2):04X}")
                cw2 = decode_SW2(int(cw2))
                self.lbl_tel_ready.setText("Готов" if
                cw2["ready"] else "Не готов")
                self.lbl_tel_motor_sel.setText(cw2["motor_sel"])
                self.lbl_tel_motor_type.setText(cw2["motor_type"])
                self.lbl_tel_overload.setText("Есть" if cw2["overload"] else "Нет")
                self.lbl_tel_ctrl_src.setText(cw2["ctrl_src"])
                self.lbl_tel_mode.setText(cw2["mode"])
                self.lbl_tel_position.setText("Вкл" if cw2["position"] else "Выкл")
                self.lbl_tel_vector.setText(cw2["vector"])
            else:
                for w in (
                    self.lbl_tel_ready,
                    self.lbl_tel_motor_sel,
                    self.lbl_tel_motor_type,
                    self.lbl_tel_overload,
                    self.lbl_tel_ctrl_src,
                    self.lbl_tel_mode,
                    self.lbl_tel_position,
                    self.lbl_tel_vector,
                    self.lbl_tel_state2_raw,
                ):
                    w.setText("—")
                # второе чтение
            self._submit(self.modbus.read_holding, after_SWs_first_16, 0x3000, 16)  # 16 адресов максимум       

        # первое чтение
        self._submit(self.modbus.read_holding, read_cw, 0x2100, 4)

    # --- RI350 setpoints handlers ---
    def set_register_value(self, spinbox, address: int, scale: float, title: str) -> None:
        value = spinbox
        # value = float(spinbox.value())
        print(f"{value=}  {address=}")
        reg_val = int(round(value * scale))
        def after(ok: bool) -> None:
            self.log(
                f"{self.DEVICE}: задать {title} {value:.2f} (0x{reg_val:04X}) → регистр 0x{address:04X} — "
                f"{'OK' if ok else 'ОШИБКА'}"
            )
        print(reg_val)
        self._submit(self.modbus.write_single_register, after, address, bin(reg_val))

    def on_set_frequency(self) -> None:
        self.set_register_value(self.spin_freq, 0x2001, 100, "частоту (Гц)")

    def on_read_frequency(self) -> None:  # <-- Исправлено имя метода
        address = 0x3000

        def after(data: Optional[List[int]]) -> None:
            if not data:
                self.log("RI350: чтение частоты — пусто")
                return
            hz = (data[0] or 0) / 100.0
            self.spin_freq.setValue(hz)
            self.lbl_tel_cur_freq.setText(f"{hz:.2f}")
            self.log(f"RI350: текущая частота {hz:.2f} Гц из 0x{address:04X}")

        self._submit(self.modbus.read_holding, after, address, 1)

    def on_set_pid(self) -> None:
        percent = float(self.spin_pid_set.value())
        reg_val = int(round(percent * 10))  # 0.1% units; 100.0% -> 1000
        address = 0x2002

        def after(ok: bool) -> None:
            self.log(
                f"RI350: задать ПИД {percent:.1f}% (0x{reg_val:04X}) → регистр 0x{address:04X} — "
                f"{'OK' if ok else 'ОШИБКА'}"
            )

        self._submit(self.modbus.write_single_register, after, address, reg_val)

    def on_read_pid(self) -> None:
        address = 0x2002

        def after(data: Optional[List[int]]) -> None:
            if not data:
                self.log("RI350: чтение ПИД — пусто")
                return
            percent = (data[0] or 0) / 10.0
            self.spin_pid_set.setValue(percent)
            self.log(f"RI350: текущий ПИД {percent:.1f}% из 0x{address:04X}")

        self._submit(self.modbus.read_holding, after, address, 1)

    # --- Helpers ---
    def log(self, message: str, level: str = "info") -> None:
        """Логирование сообщений с цветовой маркировкой по уровню."""
        color = {"info": "#000", "error": "#a00", "success": "#0a0"}.get(level, "#000")
        self.text_log.appendHtml(f'<span style="color:{color}">{message}</span>')
        self.text_log.verticalScrollBar().setValue(
            self.text_log.verticalScrollBar().maximum()
        )

    def show_error(self, msg: str) -> None:
        """Показать всплывающее окно ошибки и залогировать её."""
        self.log(msg, level="error")
        QtWidgets.QMessageBox.critical(self, "Ошибка", msg)

    def _set_status(self, ok: bool) -> None:
        self.lbl_status.setText("Подключено" if ok else "Отключено")
        self.lbl_status.setStyleSheet("color: #0a0;" if ok else "color: #a00;")
        self._connected = bool(ok)

    def _submit(self, fn, on_result, *args, **kwargs) -> None:
        job = Runnable(fn, *args, **kwargs)
        job.signals.result.connect(on_result)
        job.signals.error.connect(lambda e: self.show_error(f"Ошибка: {e}"))
        self.thread_pool.start(job)

    def _start_telemetry_timer(self) -> None:
        self.telemetry_timer.stop()
        self.telemetry_timer.setInterval(int(self.spin_tel_period.value()))
        if self._connected and self.chk_tel_auto.isChecked():
            self.telemetry_timer.start()

    # --- Slots ---
    def on_connect(self) -> None:
        host = self.edit_ip.text().strip()
        port = int(self.spin_port.value())
        unit = int(self.spin_unit.value())
        self.modbus.configure(host, port, unit)

        def after_connect(ok: bool) -> None:
            self._set_status(bool(ok))
            self.log(
                f"Подключение к {host}:{port} — {'OK' if ok else 'Не удалось подключиться'}"
            )
            if ok:
                # Включаем автообновление и сразу читаем телеметрию
                self.chk_tel_auto.setChecked(True)
                self._start_telemetry_timer()
                self.on_refresh_telemetry()

        self._submit(self.modbus.open, after_connect)

    def on_disconnect(self) -> None:
        self.modbus.close()
        self._set_status(False)
        self.log("Соединение закрыто")
        self.telemetry_timer.stop()

    def on_read(self) -> None:
        func = self.combo_read_func.currentText()
        address = int(self.spin_read_address.value())
        quantity = int(self.spin_read_quantity.value())

        def display_result(data) -> None:
            if data is None:
                self.log("Чтение вернуло пустой результат (None)")
                return
            self.table_read.setRowCount(quantity)
            for i in range(quantity):
                addr_item = QtWidgets.QTableWidgetItem(str(address + i))
                val = data[i] if i < len(data) else None
                val_item = QtWidgets.QTableWidgetItem(str(val))
                self.table_read.setItem(i, 0, addr_item)
                self.table_read.setItem(i, 1, val_item)
            self.log(
                f"Прочитано {len(data) if data else 0} значений c адреса {address}"
            )

        if func.startswith("Holding"):
            self._submit(self.modbus.read_holding, display_result, address, quantity)
        elif func.startswith("Input"):
            self._submit(self.modbus.read_input, display_result, address, quantity)
        elif func.startswith("Coils"):
            self._submit(self.modbus.read_coils, display_result, address, quantity)
        else:
            self._submit(
                self.modbus.read_discrete_inputs, display_result, address, quantity
            )

    def on_write(self) -> None:
        func = self.combo_write_func.currentText()
        address = int(self.spin_write_address.value())
        raw = self.edit_values.text().strip()

        if not raw:
            self.log("Введите значение(я) для записи")
            return

        if func.startswith("Single Register"):
            try:
                value = int(raw, 0)
            except ValueError:
                self.log("Некорректное значение регистра")
                return

            def after_single_reg(ok: bool) -> None:
                self.log(
                    f"Запись регистра {address} = {value} — {'OK' if ok else 'ОШИБКА'}"
                )

            self._submit(
                self.modbus.write_single_register, after_single_reg, address, value
            )
            return

        if func.startswith("Multiple Registers"):
            try:
                values = [int(x.strip(), 0) for x in raw.split(",") if x.strip()]
            except ValueError:
                self.log("Некорректные значения регистров")
                return

            def after_multi_reg(ok: bool) -> None:
                self.log(
                    f"Запись {len(values)} регистров с адреса {address} — "
                    f"{'OK' if ok else 'ОШИБКА'}"
                )

            self._submit(
                self.modbus.write_multiple_registers, after_multi_reg, address, values
            )
            return

        if func.startswith("Single Coil"):
            text = raw.lower()
            if text in ("1", "true", "on"):
                value_bool = True
            elif text in ("0", "false", "off"):
                value_bool = False
            else:
                self.log("Некорректное значение катушки (исп. true/false или 1/0)")
                return

            def after_single_coil(ok: bool) -> None:
                self.log(
                    f"Запись катушки {address} = {value_bool} — "
                    f"{'OK' if ok else 'ОШИБКА'}"
                )

            self._submit(
                self.modbus.write_single_coil, after_single_coil, address, value_bool
            )
            return

        # Multiple coils
        parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
        bools: List[bool] = []
        for p in parts:
            if p in ("1", "true", "on"):  # noqa: SIM103
                bools.append(True)
            elif p in ("0", "false", "off"):
                bools.append(False)
            else:
                self.log("Некорректные значения катушек (true/false, 1/0)")
                return

        def after_multi_coils(ok: bool) -> None:
            self.log(
                f"Запись {len(bools)} катушек с адреса {address} — "
                f"{'OK' if ok else 'ОШИБКА'}"
            )

        self._submit(
            self.modbus.write_multiple_coils, after_multi_coils, address, bools
        )


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    w = VFDModbusWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

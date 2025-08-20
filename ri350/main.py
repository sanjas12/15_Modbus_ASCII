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
        self.lbl_tel_cur_freq = QtWidgets.QLabel("—")
        self.lbl_tel_aim_freq = QtWidgets.QLabel("—")
        self.lbl_tel_velocity = QtWidgets.QLabel("—")

        self.btn_refresh_tel = QtWidgets.QPushButton("Обновить")
        self.chk_tel_auto = QtWidgets.QCheckBox("Автообновление")
        self.spin_tel_period = QtWidgets.QSpinBox()
        self.spin_tel_period.setRange(100, 10000)
        self.spin_tel_period.setSingleStep(100)
        self.spin_tel_period.setValue(300)

        # Auto-refresh runtime
        self.telemetry_timer = QtCore.QTimer(self)

        self._connected: bool = False
        self._tel_busy: bool = False

        # Communication RW settings 
        self.spin_freq = QtWidgets.QDoubleSpinBox()
        self.btn_set_freq = QtWidgets.QPushButton("Задать частоту")
        self.btn_read_freq = QtWidgets.QPushButton("Прочитать частоту")
        self.spin_pid_set = QtWidgets.QDoubleSpinBox()
        self.btn_set_pid = QtWidgets.QPushButton("Задать ПИД, %")
        self.btn_read_pid = QtWidgets.QPushButton("Прочитать ПИД, %")

        self.spin_pid_feedback = QtWidgets.QDoubleSpinBox()
        self.btn_set_pid_feedback = QtWidgets.QPushButton("Задать ПИД обратную связь")
        self.spin_torque = QtWidgets.QDoubleSpinBox()
        self.btn_set_torque = QtWidgets.QPushButton("Задать момент")
        self.spin_forward_freq_limit = QtWidgets.QDoubleSpinBox()
        self.btn_set_forward_freq_limit = QtWidgets.QPushButton("Задать предел прямой частоты")
        self.spin_reverse_freq_limit = QtWidgets.QDoubleSpinBox()
        self.btn_set_reverse_freq_limit = QtWidgets.QPushButton("Задать предел обратной частоты")
        self.spin_torque_limit = QtWidgets.QDoubleSpinBox()
        self.btn_set_torque_limit = QtWidgets.QPushButton("Задать предел момента")
        self.spin_brake_torque_limit = QtWidgets.QDoubleSpinBox()
        self.btn_set_brake_torque_limit = QtWidgets.QPushButton("Задать предел тормозного момента")
        self.spin_control_word = QtWidgets.QSpinBox()
        self.btn_set_control_word = QtWidgets.QPushButton("Задать управляющее слово")
        self.spin_virtual_inputs = QtWidgets.QSpinBox()
        self.btn_set_virtual_inputs = QtWidgets.QPushButton("Задать виртуальные входы")
        self.spin_virtual_outputs = QtWidgets.QSpinBox()
        self.btn_set_virtual_outputs = QtWidgets.QPushButton("Задать виртуальные выходы")
        self.spin_virtual_inputs_range = QtWidgets.QSpinBox()
        self.btn_set_virtual_inputs_range = QtWidgets.QPushButton("Задать диапазон входов")
        self.spin_voltage = QtWidgets.QDoubleSpinBox()
        self.btn_set_voltage = QtWidgets.QPushButton("Задать напряжение")
        self.spin_ao1 = QtWidgets.QDoubleSpinBox()
        self.btn_set_ao1 = QtWidgets.QPushButton("Задать АО1")
        self.spin_ao2 = QtWidgets.QDoubleSpinBox()
        self.btn_set_ao2 = QtWidgets.QPushButton("Задать АО2")


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
            lambda: self.send_ri350_command(0x0001, "Вперед")
        )
        self.btn_cmd_rev.clicked.connect(
            lambda: self.send_ri350_command(0x0002, "Назад")
        )
        self.btn_cmd_jog_fwd.clicked.connect(
            lambda: self.send_ri350_command(0x0003, "Толчок вперед")
        )
        self.btn_cmd_jog_rev.clicked.connect(
            lambda: self.send_ri350_command(0x0004, "Толчок назад")
        )
        self.btn_cmd_stop.clicked.connect(
            lambda: self.send_ri350_command(0x0005, "Стоп")
        )
        self.btn_cmd_estop.clicked.connect(
            lambda: self.send_ri350_command(0x0006, "Аварийный останов")
        )
        self.btn_cmd_reset.clicked.connect(
            lambda: self.send_ri350_command(0x0007, "Сброс ошибки")
        )
        self.btn_cmd_jog_to_stop.clicked.connect(
            lambda: self.send_ri350_command(0x0008, "Толчок для останова")
        )

        # Telemetry
        self.btn_refresh_tel.clicked.connect(self.on_refresh_telemetry)
        self.telemetry_timer.timeout.connect(self.on_refresh_telemetry)
        self.chk_tel_auto.toggled.connect(lambda _checked: self._start_telemetry_timer())
        self.spin_tel_period.valueChanged.connect(
            lambda _v: self._start_telemetry_timer()
        )

        # RI350 setpoints
        self.btn_set_freq.clicked.connect(
            lambda: self.set_register_value(self.spin_freq, 0x2001, 100, "частоту (Гц)")
        )
        self.btn_read_freq.clicked.connect(self.on_read_frequency)
        self.btn_set_pid.clicked.connect(self.on_set_pid)
        # self.btn_read_pid.clicked.connect(self.on_read_pid)

    def _build_ri350_tab(self) -> QtWidgets.QWidget:
        
        signals = Signals()
        
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

        # Communication RW settings
        row = 6
        freq_box = QtWidgets.QGroupBox("Задание частоты (регистр 0x2001, шаг 0.01 Гц)")
        freq_layout = QtWidgets.QGridLayout(freq_box)
        self.spin_freq.setDecimals(2)
        self.spin_freq.setSingleStep(0.01)
        self.spin_freq.setRange(0.00, 400.00)
        self.spin_freq.setValue(50.00)
        freq_layout.addWidget(QtWidgets.QLabel("Частота, Гц"), 0, 0)
        freq_layout.addWidget(self.spin_freq, 0, 1)
        freq_layout.addWidget(self.btn_set_freq, 0, 2)
        # freq_layout.addWidget(self.btn_read_freq, 0, 3)
        # layout.addWidget(freq_box, row, 0, 1, 2)
        row += 1

        pid_box = QtWidgets.QGroupBox("ПИД задание (регистр 0x2002, 1000 = 100.0%)")
        pid_layout = QtWidgets.QGridLayout(pid_box)
        self.spin_pid_set.setDecimals(1)
        self.spin_pid_set.setSingleStep(0.1)
        self.spin_pid_set.setRange(0.0, 100.0)
        self.spin_pid_set.setValue(0.0)
        pid_layout.addWidget(QtWidgets.QLabel("ПИД, %"), 0, 0)
        pid_layout.addWidget(self.spin_pid_set, 0, 1)
        pid_layout.addWidget(self.btn_set_pid, 0, 2)
        # pid_layout.addWidget(self.btn_read_pid, 0, 3)
        # layout.addWidget(pid_box, row, 0, 1, 2)
        row += 1
        
        com_setting_box = QtWidgets.QGroupBox("Communication RW settings ")
        com_setting_layout = QtWidgets.QGridLayout(com_setting_box)
        
        # Список параметров: (label, spinbox, button)
        param_widgets = [
            ("Задание частоты", self.spin_freq, self.btn_set_freq),
            ("ПИД задание ", self.spin_pid_set, self.btn_set_pid),
            ("Обратная связь ПИД", self.spin_pid_feedback, self.btn_set_pid_feedback),
            ("Задание момента", self.spin_torque, self.btn_set_torque),
            ("Задание верхнего предела частоты прямого вращения", self.spin_forward_freq_limit, self.btn_set_forward_freq_limit),
            ("Задание верхнего предела частоты обратного вращения", self.spin_reverse_freq_limit, self.btn_set_reverse_freq_limit),
            ("Верхний предел крутящего момента", self.spin_torque_limit, self.btn_set_torque_limit),
            ("Верхний предел тормозного момента", self.spin_brake_torque_limit, self.btn_set_brake_torque_limit),
            ("Специальное управляющее командное слово", self.spin_control_word, self.btn_set_control_word),
            ("Команда виртуальных входных клемм, диапазон", self.spin_virtual_inputs, self.btn_set_virtual_inputs),
            ("Команда виртуальных выходных клемм, диапазон", self.spin_virtual_outputs, self.btn_set_virtual_outputs),
            ("Команда виртуальных входных клемм, диапазон", self.spin_virtual_inputs_range, self.btn_set_virtual_inputs_range),
            ("Задание напряжения (используется для разделения U/F", self.spin_voltage, self.btn_set_voltage),
            ("Задание выхода АО1", self.spin_ao1, self.btn_set_ao1),
            ("Задание выхода АО2", self.spin_ao2, self.btn_set_ao2),
        ]
        for row, (label, spinbox, button) in enumerate(param_widgets):
            com_setting_layout.addWidget(QtWidgets.QLabel(label), row, 0)
            com_setting_layout.addWidget(spinbox, row, 1)
            com_setting_layout.addWidget(button, row, 2)

        layout.addWidget(com_setting_box, row, 0, 1, 2)

        return page

    def send_ri350_command(self, code: int, title: str) -> None:
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

        layout.addWidget(self.btn_refresh_tel, r, 0)
        layout.addWidget(self.chk_tel_auto, r, 1)
        layout.addWidget(QtWidgets.QLabel("Период, мс"), r, 2)
        layout.addWidget(self.spin_tel_period, r, 3)

        r=0
        # Параллельная колонка с текущей частотой (справа сверху)
        layout.addWidget(QtWidgets.QLabel("Рабочая частота, Гц"), r, 2)
        layout.addWidget(self.lbl_tel_cur_freq, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Заданная частота, Гц"), r, 2)
        layout.addWidget(self.lbl_tel_aim_freq, r, 3)
        r+=1
        layout.addWidget(QtWidgets.QLabel("Скорость вращения, об/мин"), r, 2)
        layout.addWidget(self.lbl_tel_velocity, r, 3)
        
        return page

    def on_refresh_telemetry(self) -> None:
        if self._tel_busy:
            return
        self._tel_busy = True

        # Читаем 0x2100 (SW1) → 0x2101(SW2) → 0x3000(6 байт) -> all_RW  по цепочке
        def finish():
            # Сбрасываем флаг в конце любой ветки
            self._tel_busy = False

        def after_SWs(data: Optional[List[int]]) -> None:
            """разбираем массив данных из ПЧ"""
            try:
                if data and len(data) >= 3:
                    hz = (data[0] or 0) / 100.0
                    # hz0 = (data[0] or 0) / 100.0 if data[0] is not None else None
                    aim_hz = (data[1] or 0) / 100.0 if data[1] is not None else None
                    velocity = (data[5] or 0) if data[5] is not None else None
                    self.lbl_tel_cur_freq.setText(f"{hz:.2f}")
                    self.lbl_tel_aim_freq.setText(f"{aim_hz:.2f}")
                    self.lbl_tel_velocity.setText(f"{velocity:.2f}")
                else:
                    self.lbl_tel_cur_freq.setText("—")
                    self.lbl_tel_aim_freq.setText("—")
                    self.lbl_tel_velocity.setText("—")
            finally:
                finish()

        def all_RW(data: Optional[List[int]]) -> None:
            """разбираем массив данных из ПЧ"""
            try:
                if data and len(data) >= 3:
                    hz = (data[0] or 0) / 100.0
                    # hz0 = (data[0] or 0) / 100.0 if data[0] is not None else None
                    aim_hz = (data[1] or 0) / 100.0 if data[1] is not None else None
                    velocity = (data[5] or 0) if data[5] is not None else None
                    self.lbl_tel_cur_freq.setText(f"{hz:.2f}")
                    self.lbl_tel_aim_freq.setText(f"{aim_hz:.2f}")
                    self.lbl_tel_velocity.setText(f"{velocity:.2f}")
                else:
                    self.lbl_tel_cur_freq.setText("—")
                    self.lbl_tel_aim_freq.setText("—")
                    self.lbl_tel_velocity.setText("—")
            finally:
                finish()
        

        def read_cw2(data2: Optional[List[int]]) -> None:
            try:
                val2 = data2[0] if data2 and len(data2) > 0 else None
                if val2 is not None:
                    cw2 = decode_SW2(int(val2))
                    self.lbl_tel_ready.setText("Готов" if cw2["ready"] else "Не готов")
                    self.lbl_tel_motor_sel.setText(cw2["motor_sel"])
                    self.lbl_tel_motor_type.setText(cw2["motor_type"])
                    self.lbl_tel_overload.setText("Есть" if cw2["overload"] else "Нет")
                    self.lbl_tel_ctrl_src.setText(cw2["ctrl_src"])
                    self.lbl_tel_mode.setText(cw2["mode"])
                    self.lbl_tel_position.setText("Вкл" if cw2["position"] else "Выкл")
                    self.lbl_tel_vector.setText(cw2["vector"])
                    self.lbl_tel_state2_raw.setText(f"0x{int(val2):04X}")
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
            finally:
                # Третье чтение — частота
                self._submit(self.modbus.read_holding, after_SWs, 0x3000, 6)


        def read_cw1(data1: Optional[List[int]]) -> None:
            val1 = data1[0] if data1 and len(data1) > 0 else None
            if val1 is not None:
                self.lbl_tel_state1.setText(decode_SW1(int(val1)))
                self.lbl_tel_state1_raw.setText(f"0x{int(val1):04X}")
            else:
                self.lbl_tel_state1.setText("—")
                self.lbl_tel_state1_raw.setText("—")
            # второе чтение
            self._submit(self.modbus.read_holding, read_cw2, 0x2101, 1)

        # первое чтение
        self._submit(self.modbus.read_holding, read_cw1, 0x2100, 1)

    # --- RI350 setpoints handlers ---
    def set_register_value(self, spinbox: QtWidgets.QDoubleSpinBox, address: int, scale: float, title: str) -> None:
        value = float(spinbox.value())
        reg_val = int(round(value * scale))
        def after(ok: bool) -> None:
            self.log(
                f"{self.DEVICE}: задать {title} {value:.2f} (0x{reg_val:04X}) → регистр 0x{address:04X} — "
                f"{'OK' if ok else 'ОШИБКА'}"
            )
        self._submit(self.modbus.write_single_register, after, address, reg_val)

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

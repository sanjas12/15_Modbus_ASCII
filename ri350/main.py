import sys
import threading
from typing import List, Optional

from PyQt5 import QtCore, QtWidgets
from modbus_client import ModbusClientWrapper
from telemetry import decode_state1, decode_state2_fields


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
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RI-350-19")
        self.resize(820, 760)

        self.modbus = ModbusClientWrapper()
        self.thread_pool = QtCore.QThreadPool.globalInstance()

        # UI controls created in __init__ to satisfy static analysis
        # Connection
        self.edit_ip = QtWidgets.QLineEdit("192.168.0.20")
        self.spin_port = QtWidgets.QSpinBox()
        self.spin_unit = QtWidgets.QSpinBox()
        self.btn_connect = QtWidgets.QPushButton("Подключиться")
        self.btn_disconnect = QtWidgets.QPushButton("Отключиться")
        self.lbl_status = QtWidgets.QLabel("Отключено")
        # Log
        self.text_log = QtWidgets.QPlainTextEdit()
        # Read tab controls
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
        # RI350 controls
        self.btn_cmd_fwd = QtWidgets.QPushButton("Вперед")
        self.btn_cmd_rev = QtWidgets.QPushButton("Назад")
        self.btn_cmd_jog_fwd = QtWidgets.QPushButton("Толчок вперед")
        self.btn_cmd_jog_rev = QtWidgets.QPushButton("Толчок назад")
        self.btn_cmd_stop = QtWidgets.QPushButton("Стоп")
        self.btn_cmd_estop = QtWidgets.QPushButton("Аварийный останов")
        self.btn_cmd_reset = QtWidgets.QPushButton("Сброс ошибки")
        self.btn_cmd_jog_to_stop = QtWidgets.QPushButton("Толчок для останова")
        # Telemetry controls
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
        # RI350 setpoints
        self.spin_freq = QtWidgets.QDoubleSpinBox()
        self.btn_set_freq = QtWidgets.QPushButton("Задать частоту")
        self.btn_read_freq = QtWidgets.QPushButton("Прочитать частоту")
        self.spin_pid_set = QtWidgets.QDoubleSpinBox()
        self.btn_set_pid = QtWidgets.QPushButton("Задать ПИД, %")
        self.btn_read_pid = QtWidgets.QPushButton("Прочитать ПИД, %")

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        # Главный контейнер: горизонтально (слева UI, справа журнал)
        layout_main = QtWidgets.QHBoxLayout()
        central.setLayout(layout_main)
        # Левая и правая колонки как вложенные лэйауты
        layout = QtWidgets.QVBoxLayout()
        layout_2 = QtWidgets.QVBoxLayout()

        # Connection controls
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

        # Tabs for operations
        tabs = QtWidgets.QTabWidget()
        # tabs.addTab(self._build_read_tab(), "Чтение")
        # tabs.addTab(self._build_write_tab(), "Запись")
        tabs.addTab(self._build_ri350_tab(), "RI350")

        # Log
        log_box = QtWidgets.QGroupBox("Журнал")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        self.text_log.setReadOnly(True)
        # Сделаем окно журнала крупнее по высоте
        self.text_log.setMinimumHeight(400)
        log_layout.addWidget(self.text_log)

        layout.addWidget(conn_box)
        layout.addWidget(tabs)
        # Telemetry group below RI350 tab and before log
        layout.addWidget(self._build_telemetry_group())
                
        layout_2.addWidget(log_box)

        layout_main.addLayout(layout)
        layout_main.addLayout(layout_2)

    def _build_read_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)

        self.combo_read_func.addItems([
            "Holding Registers (0x03)",
            "Input Registers (0x04)",
            "Coils (0x01)",
            "Discrete Inputs (0x02)",
        ])
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

        self.combo_write_func.addItems([
            "Single Register (0x06)",
            "Multiple Registers (0x10)",
            "Single Coil (0x05)",
            "Multiple Coils (0x0F)",
        ])
        self.spin_write_address.setRange(0, 65535)
        self.edit_values.setPlaceholderText("значения через запятую, напр.: 100,200,300 или true,false")

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
        self.btn_cmd_fwd.clicked.connect(lambda: self.send_ri350_command(0x0001, "Вперед"))
        self.btn_cmd_rev.clicked.connect(lambda: self.send_ri350_command(0x0002, "Назад"))
        self.btn_cmd_jog_fwd.clicked.connect(lambda: self.send_ri350_command(0x0003, "Толчок вперед"))
        self.btn_cmd_jog_rev.clicked.connect(lambda: self.send_ri350_command(0x0004, "Толчок назад"))
        self.btn_cmd_stop.clicked.connect(lambda: self.send_ri350_command(0x0005, "Стоп"))
        self.btn_cmd_estop.clicked.connect(lambda: self.send_ri350_command(0x0006, "Аварийный останов"))
        self.btn_cmd_reset.clicked.connect(lambda: self.send_ri350_command(0x0007, "Сброс ошибки"))
        self.btn_cmd_jog_to_stop.clicked.connect(lambda: self.send_ri350_command(0x0008, "Толчок для останова"))
        # Telemetry
        self.btn_refresh_tel.clicked.connect(self.on_refresh_telemetry)
        self.telemetry_timer.timeout.connect(self.on_refresh_telemetry)
        self.chk_tel_auto.toggled.connect(lambda _checked: self._start_telemetry_timer())
        self.spin_tel_period.valueChanged.connect(lambda _v: self._start_telemetry_timer())
        self.telemetry_timer.timeout.connect(self.on_refresh_telemetry)
        self.chk_tel_auto.toggled.connect(lambda _checked: self._start_telemetry_timer())
        self.spin_tel_period.valueChanged.connect(lambda _v: self._start_telemetry_timer())
        # RI350 setpoints
        self.btn_set_freq.clicked.connect(self.on_set_frequency)
        self.btn_read_freq.clicked.connect(self.on_read_frequency)
        self.btn_set_pid.clicked.connect(self.on_set_pid)
        self.btn_read_pid.clicked.connect(self.on_read_pid)

    def _build_ri350_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)

        # Layout: 2 columns of commands
        layout.addWidget(QtWidgets.QLabel("Команды управления (регистр 0x2000)"), 0, 0, 1, 2)
        layout.addWidget(self.btn_cmd_fwd, 1, 0)
        layout.addWidget(self.btn_cmd_rev, 1, 1)
        layout.addWidget(self.btn_cmd_jog_fwd, 2, 0)
        layout.addWidget(self.btn_cmd_jog_rev, 2, 1)
        layout.addWidget(self.btn_cmd_stop, 3, 0)
        layout.addWidget(self.btn_cmd_estop, 3, 1)
        layout.addWidget(self.btn_cmd_reset, 4, 0)
        layout.addWidget(self.btn_cmd_jog_to_stop, 4, 1)

        # Setpoints section
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
        freq_layout.addWidget(self.btn_read_freq, 0, 3)
        layout.addWidget(freq_box, row, 0, 1, 2)

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
        pid_layout.addWidget(self.btn_read_pid, 0, 3)
        layout.addWidget(pid_box, row, 0, 1, 2)

        return page

    def send_ri350_command(self, code: int, title: str) -> None:
        address = 0x2000
        def after(ok: bool) -> None:
            self.log(f"RI350: {title} → регистр 0x{address:04X} значение 0x{code:04X} — {'OK' if ok else 'ОШИБКА'}")
        self._submit(self.modbus.write_single_register, after, address, int(code))

    # --- Telemetry (address_R) ---
    def _build_telemetry_group(self) -> QtWidgets.QGroupBox:
        page = QtWidgets.QGroupBox("Телеметрия")
        layout = QtWidgets.QGridLayout(page)

        r = 0
        layout.addWidget(QtWidgets.QLabel("ПЧ слово состояния 1 (0x2100)"), r, 0, 1, 2); r += 1
        layout.addWidget(QtWidgets.QLabel("Состояние"), r, 0)
        layout.addWidget(self.lbl_tel_state1, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("RAW"), r, 0)
        layout.addWidget(self.lbl_tel_state1_raw, r, 1); r += 1

        layout.addWidget(QtWidgets.QLabel("ПЧ слово состояния 2 (0x2101)"), r, 0, 1, 2); r += 1
        layout.addWidget(QtWidgets.QLabel("Готов к запуску"), r, 0)
        layout.addWidget(self.lbl_tel_ready, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Выбран двигатель"), r, 0)
        layout.addWidget(self.lbl_tel_motor_sel, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Тип двигателя"), r, 0)
        layout.addWidget(self.lbl_tel_motor_type, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Авария перегрузки"), r, 0)
        layout.addWidget(self.lbl_tel_overload, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Источник управления"), r, 0)
        layout.addWidget(self.lbl_tel_ctrl_src, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Режим управления"), r, 0)
        layout.addWidget(self.lbl_tel_mode, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Позиционное управление"), r, 0)
        layout.addWidget(self.lbl_tel_position, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("Тип вектора"), r, 0)
        layout.addWidget(self.lbl_tel_vector, r, 1); r += 1
        layout.addWidget(QtWidgets.QLabel("RAW"), r, 0)
        layout.addWidget(self.lbl_tel_state2_raw, r, 1); r += 1

        layout.addWidget(self.btn_refresh_tel, r, 0)
        layout.addWidget(self.chk_tel_auto, r, 1)
        layout.addWidget(QtWidgets.QLabel("Период, мс"), r, 2)
        layout.addWidget(self.spin_tel_period, r, 3)

        return page

    @staticmethod
    def _decode_state1(value: int) -> str:
        mapping = {
            0x0001: "Вперед",
            0x0002: "Назад",
            0x0003: "Останов",
            0x0004: "Ошибка",
            0x0005: "POFF",
            0x0006: "Предварительное возбуждение",
        }
        return mapping.get(value, f"Неизвестно (0x{value:04X})")

    @staticmethod
    def _decode_state2_fields(value: int) -> dict:
        ready = bool(value & (1 << 0))
        motor_sel_bits = (value >> 1) & 0b11
        motor_sel = "Двигатель 1" if motor_sel_bits == 0 else ("Двигатель 2" if motor_sel_bits == 1 else f"Код {motor_sel_bits}")
        motor_type = "Синхронный" if (value & (1 << 3)) else "Асинхронный"
        overload = bool(value & (1 << 4))
        ctrl_src_bits = (value >> 5) & 0b11
        ctrl_src = {0: "Клавиатура", 1: "Терминал", 2: "Связь"}.get(ctrl_src_bits, f"Код {ctrl_src_bits}")
        mode = "Крутящий момент" if (value & (1 << 8)) else "Скорость"
        position = bool(value & (1 << 9))
        vector_bits = (value >> 10) & 0b11
        vector_map = {0: "Вектор 0", 1: "Вектор 1", 2: "Вектор замкн. контура", 3: "Вектор напр. пространства"}
        vector = vector_map.get(vector_bits, f"Код {vector_bits}")
        return {
            "ready": ready,
            "motor_sel": motor_sel,
            "motor_type": motor_type,
            "overload": overload,
            "ctrl_src": ctrl_src,
            "mode": mode,
            "position": position,
            "vector": vector,
        }

    def on_refresh_telemetry(self) -> None:
        if getattr(self, "_tel_busy", False):
            return
        self._tel_busy = True
        # Read 0x2100 and 0x2101 sequentially and update labels
        def after_first(data1: Optional[List[int]]):
            val1 = data1[0] if data1 and len(data1) > 0 else None
            if val1 is not None:
                self.lbl_tel_state1.setText(decode_state1(int(val1)))
                self.lbl_tel_state1_raw.setText(f"0x{int(val1):04X}")
            else:
                self.lbl_tel_state1.setText("—")
                self.lbl_tel_state1_raw.setText("—")

            def after_second(data2: Optional[List[int]]):
                val2 = data2[0] if data2 and len(data2) > 0 else None
                if val2 is not None:
                    fields = decode_state2_fields(int(val2))
                    self.lbl_tel_ready.setText("Готов" if fields["ready"] else "Не готов")
                    self.lbl_tel_motor_sel.setText(fields["motor_sel"])
                    self.lbl_tel_motor_type.setText(fields["motor_type"])
                    self.lbl_tel_overload.setText("Есть" if fields["overload"] else "Нет")
                    self.lbl_tel_ctrl_src.setText(fields["ctrl_src"])
                    self.lbl_tel_mode.setText(fields["mode"])
                    self.lbl_tel_position.setText("Вкл" if fields["position"] else "Выкл")
                    self.lbl_tel_vector.setText(fields["vector"])
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

            self._submit(self.modbus.read_holding, after_second, 0x2101, 1)

        def release_flag(_res=None):
            self._tel_busy = False

        # chain completion to reset busy flag
        def wrapped_after_first(data1: Optional[List[int]]):
            try:
                after_first(data1)
            finally:
                release_flag()

        self._submit(self.modbus.read_holding, wrapped_after_first, 0x2100, 1)

    # --- RI350 setpoints handlers ---
    def on_set_frequency(self) -> None:
        hz = float(self.spin_freq.value())
        reg_val = int(round(hz * 100))  # 0.01 Hz units
        address = 0x2001
        def after(ok: bool) -> None:
            self.log(f"RI350: задать частоту {hz:.2f} Гц (0x{reg_val:04X}) → регистр 0x{address:04X} — {'OK' if ok else 'ОШИБКА'}")
        self._submit(self.modbus.write_single_register, after, address, reg_val)

    def on_read_frequency(self) -> None:
        address = 0x3000
        def after(data: Optional[List[int]]) -> None:
            if not data:
                self.log("RI350: чтение частоты — пусто")
                return
            hz = (data[0] or 0) / 100.0
            self.spin_freq.setValue(hz)
            self.log(f"RI350: текущая частота {hz:.2f} Гц из 0x{address:04X}")
        self._submit(self.modbus.read_holding, after, address, 1)

    def on_set_pid(self) -> None:
        percent = float(self.spin_pid_set.value())
        reg_val = int(round(percent * 10))  # 0.1% units; 100.0% -> 1000
        address = 0x2002
        def after(ok: bool) -> None:
            self.log(f"RI350: задать ПИД {percent:.1f}% (0x{reg_val:04X}) → регистр 0x{address:04X} — {'OK' if ok else 'ОШИБКА'}")
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
    def log(self, message: str) -> None:
        self.text_log.appendPlainText(message)
        self.text_log.verticalScrollBar().setValue(self.text_log.verticalScrollBar().maximum())

    def _set_status(self, ok: bool) -> None:
        self.lbl_status.setText("Подключено" if ok else "Отключено")
        self.lbl_status.setStyleSheet("color: #0a0;" if ok else "color: #a00;")
        self._connected = bool(ok)

    def _submit(self, fn, on_result, *args, **kwargs) -> None:
        job = Runnable(fn, *args, **kwargs)
        job.signals.result.connect(on_result)
        job.signals.error.connect(lambda e: self.log(f"Ошибка: {e}"))
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
            self.log(f"Подключение к {host}:{port} — {'OK' if ok else 'Нет подключания'}")
            if ok:
                # Автоматически включаем автообновление и делаем мгновенное обновление
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
            # fill table
            self.table_read.setRowCount(quantity)
            for i in range(quantity):
                addr_item = QtWidgets.QTableWidgetItem(str(address + i))
                val = data[i] if i < len(data) else None
                val_item = QtWidgets.QTableWidgetItem(str(val))
                self.table_read.setItem(i, 0, addr_item)
                self.table_read.setItem(i, 1, val_item)
            self.log(f"Прочитано {len(data) if data else 0} значений c адреса {address}")

        if func.startswith("Holding"):
            self._submit(self.modbus.read_holding, display_result, address, quantity)
        elif func.startswith("Input"):
            self._submit(self.modbus.read_input, display_result, address, quantity)
        elif func.startswith("Coils"):
            self._submit(self.modbus.read_coils, display_result, address, quantity)
        else:
            self._submit(self.modbus.read_discrete_inputs, display_result, address, quantity)

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
                self.log(f"Запись регистра {address} = {value} — {'OK' if ok else 'ОШИБКА'}")

            self._submit(self.modbus.write_single_register, after_single_reg, address, value)
            return

        if func.startswith("Multiple Registers"):
            try:
                values = [int(x.strip(), 0) for x in raw.split(",") if x.strip()]
            except ValueError:
                self.log("Некорректные значения регистров")
                return

            def after_multi_reg(ok: bool) -> None:
                self.log(
                    f"Запись {len(values)} регистров с адреса {address} — {'OK' if ok else 'ОШИБКА'}"
                )

            self._submit(self.modbus.write_multiple_registers, after_multi_reg, address, values)
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
                self.log(f"Запись катушки {address} = {value_bool} — {'OK' if ok else 'ОШИБКА'}")

            self._submit(self.modbus.write_single_coil, after_single_coil, address, value_bool)
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
                f"Запись {len(bools)} катушек с адреса {address} — {'OK' if ok else 'ОШИБКА'}"
            )

        self._submit(self.modbus.write_multiple_coils, after_multi_coils, address, bools)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    w = VFDModbusWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())



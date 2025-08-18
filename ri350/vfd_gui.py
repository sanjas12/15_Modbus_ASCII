import sys
import threading
from typing import List, Optional

from pyModbusTCP.client import ModbusClient
from PyQt5 import QtCore, QtWidgets


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


class ModbusClientWrapper:
    def __init__(self) -> None:
        # Client is created in configure()
        self._client: Optional[ModbusClient] = None
        self._lock = threading.Lock()

    def _is_open(self) -> bool:
        if self._client is None:
            return False
        is_open_attr = getattr(self._client, "is_open", None)
        if callable(is_open_attr):
            return bool(is_open_attr())
        if isinstance(is_open_attr, bool):
            return is_open_attr
        return False

    def configure(self, host: str, port: int, unit_id: int) -> None:
        with self._lock:
            if self._client is not None and self._is_open():
                self._client.close()
            # Recreate client with explicit params to avoid API ambiguity
            self._client = ModbusClient(
                host=host,
                port=port,
                unit_id=unit_id,
                auto_open=True,
                auto_close=False,
                timeout=3.0,
            )

    def open(self) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            if not self._is_open():
                return self._client.open()
            return True

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()

    # --- Read operations ---
    def read_holding(self, address: int, quantity: int) -> Optional[List[int]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return self._client.read_holding_registers(address, quantity)

    def read_input(self, address: int, quantity: int) -> Optional[List[int]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return self._client.read_input_registers(address, quantity)

    def read_coils(self, address: int, quantity: int) -> Optional[List[bool]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return self._client.read_coils(address, quantity)

    def read_discrete_inputs(self, address: int, quantity: int) -> Optional[List[bool]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return self._client.read_discrete_inputs(address, quantity)

    # --- Write operations ---
    def write_single_register(self, address: int, value: int) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return bool(self._client.write_single_register(address, value))

    def write_multiple_registers(self, address: int, values: List[int]) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return bool(self._client.write_multiple_registers(address, values))

    def write_single_coil(self, address: int, value: bool) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return bool(self._client.write_single_coil(address, value))

    def write_multiple_coils(self, address: int, values: List[bool]) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Клиент не сконфигурирован")
            return bool(self._client.write_multiple_coils(address, values))


class VFDModbusWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VFD Modbus TCP")
        self.resize(820, 560)

        self.modbus = ModbusClientWrapper()
        self.thread_pool = QtCore.QThreadPool.globalInstance()

        # UI controls created in __init__ to satisfy static analysis
        # Connection
        self.edit_ip = QtWidgets.QLineEdit("192.168.0.1")
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

        layout = QtWidgets.QVBoxLayout(central)

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
        log_layout.addWidget(self.text_log)

        layout.addWidget(conn_box)
        layout.addWidget(tabs)
        layout.addWidget(log_box)

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

    # --- RI350 setpoints handlers ---
    def on_set_frequency(self) -> None:
        hz = float(self.spin_freq.value())
        reg_val = int(round(hz * 100))  # 0.01 Hz units
        address = 0x2001
        def after(ok: bool) -> None:
            self.log(f"RI350: задать частоту {hz:.2f} Гц (0x{reg_val:04X}) → регистр 0x{address:04X} — {'OK' if ok else 'ОШИБКА'}")
        self._submit(self.modbus.write_single_register, after, address, reg_val)

    def on_read_frequency(self) -> None:
        address = 0x2001
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

    def _submit(self, fn, on_result, *args, **kwargs) -> None:
        job = Runnable(fn, *args, **kwargs)
        job.signals.result.connect(on_result)
        job.signals.error.connect(lambda e: self.log(f"Ошибка: {e}"))
        self.thread_pool.start(job)

    # --- Slots ---
    def on_connect(self) -> None:
        host = self.edit_ip.text().strip()
        port = int(self.spin_port.value())
        unit = int(self.spin_unit.value())
        self.modbus.configure(host, port, unit)

        def after_connect(ok: bool) -> None:
            self._set_status(bool(ok))
            self.log(f"Подключение к {host}:{port} — {'OK' if ok else 'НЕ УДАЛОСЬ'}")

        self._submit(self.modbus.open, after_connect)

    def on_disconnect(self) -> None:
        self.modbus.close()
        self._set_status(False)
        self.log("Соединение закрыто")

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



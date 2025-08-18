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

    def configure(self, host: str, port: int, unit_id: int) -> None:
        with self._lock:
            if self._client is not None and self._client.is_open():
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
            if not self._client.is_open():
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

        # Predeclare attributes for linters
        self.edit_ip = None
        self.spin_port = None
        self.spin_unit = None
        self.btn_connect = None
        self.btn_disconnect = None
        self.lbl_status = None
        self.text_log = None
        self.combo_read_func = None
        self.spin_read_address = None
        self.spin_read_quantity = None
        self.btn_read = None
        self.table_read = None
        self.combo_write_func = None
        self.spin_write_address = None
        self.edit_values = None
        self.btn_write = None

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)

        # Connection controls
        conn_box = QtWidgets.QGroupBox("Подключение")
        conn_layout = QtWidgets.QGridLayout(conn_box)
        self.edit_ip = QtWidgets.QLineEdit("192.168.0.10")
        self.spin_port = QtWidgets.QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(502)
        self.spin_unit = QtWidgets.QSpinBox()
        self.spin_unit.setRange(0, 255)
        self.spin_unit.setValue(1)
        self.btn_connect = QtWidgets.QPushButton("Подключиться")
        self.btn_disconnect = QtWidgets.QPushButton("Отключиться")
        self.lbl_status = QtWidgets.QLabel("Отключено")
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
        tabs.addTab(self._build_read_tab(), "Чтение")
        tabs.addTab(self._build_write_tab(), "Запись")

        # Log
        log_box = QtWidgets.QGroupBox("Журнал")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        self.text_log = QtWidgets.QPlainTextEdit()
        self.text_log.setReadOnly(True)
        log_layout.addWidget(self.text_log)

        layout.addWidget(conn_box)
        layout.addWidget(tabs)
        layout.addWidget(log_box)

    def _build_read_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(page)

        self.combo_read_func = QtWidgets.QComboBox()
        self.combo_read_func.addItems([
            "Holding Registers (0x03)",
            "Input Registers (0x04)",
            "Coils (0x01)",
            "Discrete Inputs (0x02)",
        ])
        self.spin_read_address = QtWidgets.QSpinBox()
        self.spin_read_address.setRange(0, 65535)
        self.spin_read_quantity = QtWidgets.QSpinBox()
        self.spin_read_quantity.setRange(1, 125)
        self.spin_read_quantity.setValue(1)
        self.btn_read = QtWidgets.QPushButton("Читать")
        self.table_read = QtWidgets.QTableWidget(0, 2)
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

        self.combo_write_func = QtWidgets.QComboBox()
        self.combo_write_func.addItems([
            "Single Register (0x06)",
            "Multiple Registers (0x10)",
            "Single Coil (0x05)",
            "Multiple Coils (0x0F)",
        ])
        self.spin_write_address = QtWidgets.QSpinBox()
        self.spin_write_address.setRange(0, 65535)
        self.edit_values = QtWidgets.QLineEdit()
        self.edit_values.setPlaceholderText("значения через запятую, напр.: 100,200,300 или true,false")
        self.btn_write = QtWidgets.QPushButton("Записать")

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



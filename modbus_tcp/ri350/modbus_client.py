import threading
from typing import List, Optional

from pyModbusTCP.client import ModbusClient


class ModbusClientWrapper:
    """Thread-safe thin wrapper around pyModbusTCP ModbusClient."""

    NOT_CONNECT = "Нет соединения с ПЧ"

    def __init__(self) -> None:
        self._client: Optional[ModbusClient] = None
        self._lock = threading.Lock()

    def configure(self, host: str, port: int, unit_id: int) -> None:
        if not host or not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValueError("Неверные параметры подключения")
            
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
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
                raise RuntimeError(self.NOT_CONNECT)
            return bool(self._client.open())

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()

    def is_connected(self) -> bool:
        """Проверка, установлено ли соединение с Modbus."""
        with self._lock:
            if self._client is None:
                return False
            # is_open — это БУЛЕВО СВОЙСТВО, без скобок
            return bool(self._client.is_open)

    # --- Read operations ---
    def read_holding(self, address: int, quantity: int) -> Optional[List[int]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return self._client.read_holding_registers(address, quantity)

    def read_input(self, address: int, quantity: int) -> Optional[List[int]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return self._client.read_input_registers(address, quantity)

    def read_coils(self, address: int, quantity: int) -> Optional[List[bool]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return self._client.read_coils(address, quantity)

    def read_discrete_inputs(self, address: int, quantity: int) -> Optional[List[bool]]:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return self._client.read_discrete_inputs(address, quantity)

    # --- Write operations ---
    def write_single_register(self, address: int, value: int) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return bool(self._client.write_single_register(address, value))

    def write_multiple_registers(self, address: int, values: List[int]) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return bool(self._client.write_multiple_registers(address, values))

    def write_single_coil(self, address: int, value: bool) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return bool(self._client.write_single_coil(address, value))

    def write_multiple_coils(self, address: int, values: List[bool]) -> bool:
        with self._lock:
            if self._client is None:
                raise RuntimeError(self.NOT_CONNECT)
            return bool(self._client.write_multiple_coils(address, values))
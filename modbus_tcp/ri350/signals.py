from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from PyQt5 import QtWidgets


@dataclass
class ParameterConfig:
    """Configuration for a single parameter containing Modbus address, default value, and button name."""

    modbus_address: str  # Hexadecimal string, e.g., '0x2001'
    description: str     # Description of the parameter
    default_value: Any
    button_name: str
    range: tuple[int, int]
    single_step: float = 0.1
    spin_box: Optional[QtWidgets.QDoubleSpinBox] = None
    btn_set: Optional[QtWidgets.QPushButton] = None

    def __post_init__(self) -> None:
        if self.btn_set is None:
            self.btn_set = QtWidgets.QPushButton(self.button_name)
        if self.spin_box is None:
            self.spin_box = QtWidgets.QDoubleSpinBox()


@dataclass
class Signals:
    """Data class for storing parameters configuration with Modbus addresses, default values, and button names."""

    parameters: Dict[str, ParameterConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize predefined parameters after object creation."""
        self._init_predefined_parameters()

    def _init_predefined_parameters(self) -> None:
        """Initialize all predefined parameter configurations."""
        predefined_params = {
            "Задание частоты, шаг 0.01 Гц ": ParameterConfig(
                modbus_address="0x2001",
                description="Задание частоты, шаг 0.01 Гц",
                default_value=50,
                button_name="Задать частоту",
                range=(0, 100),
                single_step=0.01,
            ),
            "ПИД задание, %": ParameterConfig(
                modbus_address="0x2002",
                description="ПИД задание, %",
                default_value=0,
                button_name="Задать ПИД",
                range=(0, 1000),
                single_step=50,
            ),
            "Задать ПИД обратную связь": ParameterConfig(
                modbus_address="0x2003",
                description="Задать ПИД обратную связь",
                default_value=0,
                button_name="btn_set_pid_feedback",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать момент": ParameterConfig(
                modbus_address="0x2004",
                description="Задать момент",
                default_value=0,
                button_name="btn_set_torque",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать предел прямой час": ParameterConfig(
                modbus_address="0x2005",
                description="Задать предел прямой час",
                default_value=0,
                button_name="btn_set_forward_limit",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать предел обратной ч": ParameterConfig(
                modbus_address="0x2006",
                description="Задать предел обратной ч",
                default_value=0,
                button_name="btn_set_reverse_limit",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать предел момента": ParameterConfig(
                modbus_address="0x2007",
                description="Задать предел момента",
                default_value=0,
                button_name="btn_set_torque_limit",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать предел тормозного": ParameterConfig(
                modbus_address="0x2008",
                description="Задать предел тормозного",
                default_value=0,
                button_name="btn_set_brake_limit",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать управляющее слово": ParameterConfig(
                modbus_address="0x2009",
                description="Задать управляющее слово",
                default_value=0,
                button_name="btn_set_control_word",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задать виртуальные входы": ParameterConfig(
                modbus_address="0x200A",
                description="Задать виртуальные входы",
                default_value=1,
                button_name="Задать входы",
                range=(1, 2),
                single_step=1,
            ),
            "Задать виртуальные выходы": ParameterConfig(
                modbus_address="0x200B",
                description="Задать виртуальные выходы",
                default_value=0,
                button_name="Задать выходы",
                range=(0, 2),
                single_step=1,
            ),
            "Задать напряжение": ParameterConfig(
                modbus_address="0x200C",
                description="Задать напряжение",
                default_value=0,
                button_name="btn_set_voltage",
                range=(0, 100),
                single_step=0.1,
            ),
            "Задание выхода АО1": ParameterConfig(
                modbus_address="0x200D",
                description="Задание выхода АО1",
                default_value=0,
                button_name="Задать выход АО1",
                range=(-1000, 1000),
                single_step=10,
            ),
            "Задание выхода АО2": ParameterConfig(
                modbus_address="0x200E",
                description="Задание выхода АО2",
                default_value=0,
                button_name="Задать выход АО2",
                range=(-1000, 1000),
                single_step=10,
            ),
        }
        self.parameters.update(predefined_params)

    def add_parameter(
        self,
        parameter_name: str,
        modbus_address: int | str,
        default_value: Any,
        button_name: str,
        range: tuple[int, int] = (0, 100),
        single_step: float = 0.1,
    ) -> None:
        """Add a new parameter configuration.

        Args:
            parameter_name: Human-readable name of the parameter.
            modbus_address: Address of the parameter (int or hex string).
            default_value: Default value for the parameter.
            button_name: UI button name for this parameter.
            range: Allowed range of values.
            single_step: Step for spin box control.
        """
        # Унифицируем модбас-адрес в строку (hex), чтобы не было дублирования
        address_str = (
            hex(modbus_address)
            if isinstance(modbus_address, int)
            else str(modbus_address)
        )

        self.parameters[parameter_name] = ParameterConfig(
            modbus_address=address_str,
            description=parameter_name,
            default_value=default_value,
            button_name=button_name,
            range=range,
            single_step=single_step,
        )

    def get_parameter(self, parameter_name: str) -> Optional[ParameterConfig]:
        """Get parameter configuration by name."""
        return self.parameters.get(parameter_name)

    def get_modbus_address(self, parameter_name: str) -> Optional[str]:
        """Get Modbus address for a parameter."""
        param = self.parameters.get(parameter_name)
        return param.modbus_address if param else None

    def get_default_value(self, parameter_name: str) -> Any:
        """Get default value for a parameter."""
        param = self.parameters.get(parameter_name)
        return param.default_value if param else None

    def get_button_name(self, parameter_name: str) -> Optional[str]:
        """Get button name for a parameter."""
        param = self.parameters.get(parameter_name)
        return param.button_name if param else None

    def update_parameter(
        self,
        parameter_name: str,
        modbus_address: Optional[int | str] = None,
        default_value: Any = None,
        button_name: Optional[str] = None,
        single_step: Optional[float] = None,
    ) -> None:
        """Update parameter configuration."""
        if parameter_name not in self.parameters:
            return

        param = self.parameters[parameter_name]

        if modbus_address is not None:
            param.modbus_address = (
                hex(modbus_address)
                if isinstance(modbus_address, int)
                else str(modbus_address)
            )
        if default_value is not None:
            param.default_value = default_value
        if button_name is not None:
            param.button_name = button_name
        if single_step is not None:
            param.single_step = single_step

    def remove_parameter(self, parameter_name: str) -> bool:
        """Remove a parameter configuration."""
        return self.parameters.pop(parameter_name, None) is not None

    def list_parameters(self) -> list[str]:
        """List all parameter names."""
        return list(self.parameters.keys())

    def get_all_configs(self) -> Dict[str, ParameterConfig]:
        """Get all parameter configurations."""
        return self.parameters

    def __repr__(self) -> str:
        return f"Settings(parameters={len(self.parameters)} parameters)"


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    # Create QApplication before any QWidget
    app = QApplication(sys.argv)

    # Example usage:
    signals = Signals()

    for name, parameter in signals.parameters.items():
        print(f"{parameter.description=}, {parameter.btn_set=}")
        print(f"{parameter.description=}, {parameter.spin_box=}")

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ParameterConfig:
    """Configuration for a single parameter containing Modbus address, default value, and button name."""
    modbus_address: str  # Hexadecimal string, e.g., '0x2001'
    default_value: Any
    button_name: str
    range: tuple
    single_step: float = 0.1

@dataclass
class Signals:
    """Data class for storing parameters configuration with Modbus addresses, default values, and button names."""

    parameters: Dict[str, ParameterConfig] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize predefined parameters after object creation."""
        self._init_predefined_parameters()

    def _init_predefined_parameters(self):
        """Initialize all predefined parameter configurations."""
        predefined_params = {
            "Задание частоты, Гц ": ParameterConfig(
                modbus_address="0x2001",
                default_value=50,
                button_name="Задать частоту",
                range=(0, 100),
                single_step=0.1
            ),
            "ПИД задание, %": ParameterConfig(
                modbus_address="0x2002",
                default_value=0,
                button_name="Задать ПИД",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать ПИД обратную связь": ParameterConfig(
                modbus_address="0x2003",
                default_value=0,
                button_name="btn_set_pid_feedback",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать момент": ParameterConfig(
                modbus_address="0x2004",
                default_value=0,
                button_name="btn_set_torque",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать предел прямой час": ParameterConfig(
                modbus_address="0x2005",
                default_value=0,
                button_name="btn_set_forward_limit",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать предел обратной ч": ParameterConfig(
                modbus_address="0x2006",
                default_value=0,
                button_name="btn_set_reverse_limit",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать предел момента": ParameterConfig(
                modbus_address="0x2007",
                default_value=0,
                button_name="btn_set_torque_limit",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать предел тормозного": ParameterConfig(
                modbus_address="0x2008",
                default_value=0,
                button_name="btn_set_brake_limit",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать управляющее слово": ParameterConfig(
                modbus_address="0x2009",
                default_value=0,
                button_name="btn_set_control_word",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать виртуальные входы": ParameterConfig(
                modbus_address="0x200A",
                default_value=0,
                button_name="btn_set_virtual_inputs",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать виртуальные выходы": ParameterConfig(
                modbus_address="0x200B",
                default_value=0,
                button_name="btn_set_virtual_outputs",
                range=(0, 100),
                single_step=0.1
            ),
            "Задать напряжение": ParameterConfig(
                modbus_address="0x200C",
                default_value=0,
                button_name="btn_set_voltage",
                range=(0, 100),
                single_step=0.1
            ),
            "Задание выхода АО1": ParameterConfig(
                modbus_address="0x200D",
                default_value=0,
                button_name="Заданить выход АО1",
                range=(0, 100),
                single_step=0.1
            ),
            "Задание выхода АО2": ParameterConfig(
                modbus_address="0x200E",
                default_value=0,
                button_name="Заданить выход АО2",
                range=(0, 100),
                single_step=0.1
            )
        }

        self.parameters.update(predefined_params)

    def add_parameter(self, parameter_name: str, modbus_address: int, default_value: Any, button_name: str, range: tuple = (0, 100), single_step: float = 0.1) -> None:
        """Add a new parameter configuration."""
        self.parameters[parameter_name] = ParameterConfig(
            modbus_address=hex(modbus_address) if isinstance(modbus_address, int) else modbus_address,
            default_value=default_value,
            button_name=button_name,
            range=range,
            single_step=single_step
        )

    def get_parameter(self, parameter_name: str) -> ParameterConfig:
        """Get parameter configuration by name."""
        return self.parameters.get(parameter_name)

    def get_modbus_address(self, parameter_name: str) -> str:
        """Get Modbus address for a parameter."""
        param = self.parameters.get(parameter_name)
        return param.modbus_address if param else None

    def get_default_value(self, parameter_name: str) -> Any:
        """Get default value for a parameter."""
        param = self.parameters.get(parameter_name)
        return param.default_value if param else None

    def get_button_name(self, parameter_name: str) -> str:
        """Get button name for a parameter."""
        param = self.parameters.get(parameter_name)
        return param.button_name if param else None

    def update_parameter(self, parameter_name: str, modbus_address: int = None, default_value: Any = None, button_name: str = None, single_step: float = None) -> None:
        """Update parameter configuration."""
        if parameter_name in self.parameters:
            param = self.parameters[parameter_name]
            if modbus_address is not None:
                param.modbus_address = hex(modbus_address) if isinstance(modbus_address, int) else modbus_address
            if default_value is not None:
                param.default_value = default_value
            if button_name is not None:
                param.button_name = button_name
            if single_step is not None:
                param.single_step = single_step

    def remove_parameter(self, parameter_name: str) -> bool:
        """Remove a parameter configuration."""
        if parameter_name in self.parameters:
            del self.parameters[parameter_name]
            return True
        return False

    def list_parameters(self) -> list:
        """List all parameter names."""
        return list(self.parameters.keys())

    def get_all_configs(self) -> Dict[str, ParameterConfig]:
        """Get all parameter configurations."""
        return self.parameters

    def __repr__(self) -> str:
        return f"Settings(parameters={len(self.parameters)} parameters)"


if __name__ == "__main__":
    
    # Example usage:
    signals = Signals()

    for name, config in signals.parameters.items():
        print(f"{name}: {config}")

    # print(Signals.get_modbus_address("Задать частоту"))  # Output: 2001
    # print(Signals.get_default_value("Задать ПИД, %"))    # Output: 75.0
    # print(Signals.get_button_name("Задать момент"))      # Output: btn_set_torque


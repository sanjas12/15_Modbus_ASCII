from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ParameterConfig:
    """Configuration for a single parameter containing Modbus address, default value, and button name."""
    modbus_address: int
    default_value: Any
    button_name: str

@dataclass
class Settings:
    """Data class for storing parameters configuration with Modbus addresses, default values, and button names."""
    
    # Main dictionary: parameter name -> ParameterConfig
    parameters: Dict[str, ParameterConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize predefined parameters after object creation."""
        self._init_predefined_parameters()
    
    def _init_predefined_parameters(self):
        """Initialize all predefined parameter configurations."""
        predefined_params = {
            "Задать частоту": ParameterConfig(
                modbus_address=2001,
                default_value=50.0,
                button_name="btn_set_frequency"
            ),
            "Задать ПИД, %": ParameterConfig(
                modbus_address=2002,
                default_value=75.0,
                button_name="btn_set_pid_percent"
            ),
            "Задать ПИД обратную связь": ParameterConfig(
                modbus_address=2003,
                default_value=50.0,
                button_name="btn_set_pid_feedback"
            ),
            "Задать момент": ParameterConfig(
                modbus_address=2004,
                default_value=100.0,
                button_name="btn_set_torque"
            ),
            "Задать предел прямой час": ParameterConfig(
                modbus_address=2005,
                default_value=3600,
                button_name="btn_set_forward_limit"
            ),
            "Задать предел обратной ч": ParameterConfig(
                modbus_address=2006,
                default_value=3600,
                button_name="btn_set_reverse_limit"
            ),
            "Задать предел момента": ParameterConfig(
                modbus_address=2007,
                default_value=150.0,
                button_name="btn_set_torque_limit"
            ),
            "Задать предел тормозного": ParameterConfig(
                modbus_address=2008,
                default_value=100.0,
                button_name="btn_set_brake_limit"
            ),
            "Задать управляющее слово": ParameterConfig(
                modbus_address=2009,
                default_value=0,
                button_name="btn_set_control_word"
            ),
            "Задать виртуальные входы": ParameterConfig(
                modbus_address=2010,
                default_value=0,
                button_name="btn_set_virtual_inputs"
            ),
            "Задать виртуальные выходы": ParameterConfig(
                modbus_address=2011,
                default_value=0,
                button_name="btn_set_virtual_outputs"
            ),
            "Задать диапазон входов": ParameterConfig(
                modbus_address=2012,
                default_value=100.0,
                button_name="btn_set_input_range"
            ),
            "Задать напряжение": ParameterConfig(
                modbus_address=2013,
                default_value=24.0,
                button_name="btn_set_voltage"
            ),
            "Задать АО1": ParameterConfig(
                modbus_address=2014,
                default_value=4.0,
                button_name="btn_set_ao1"
            ),
            "Задать АО2": ParameterConfig(
                modbus_address=2015,
                default_value=4.0,
                button_name="btn_set_ao2"
            )
        }
        
        self.parameters.update(predefined_params)
    
    def add_parameter(self, parameter_name: str, modbus_address: int, default_value: Any, button_name: str) -> None:
        """Add a new parameter configuration."""
        self.parameters[parameter_name] = ParameterConfig(
            modbus_address=modbus_address,
            default_value=default_value,
            button_name=button_name
        )
    
    def get_parameter(self, parameter_name: str) -> ParameterConfig:
        """Get parameter configuration by name."""
        return self.parameters.get(parameter_name)
    
    def get_modbus_address(self, parameter_name: str) -> int:
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
    
    def update_parameter(self, parameter_name: str, modbus_address: int = None, default_value: Any = None, button_name: str = None) -> None:
        """Update parameter configuration."""
        if parameter_name in self.parameters:
            param = self.parameters[parameter_name]
            if modbus_address is not None:
                param.modbus_address = modbus_address
            if default_value is not None:
                param.default_value = default_value
            if button_name is not None:
                param.button_name = button_name
    
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

# Example usage:
# settings = Settings()
# print(settings.get_modbus_address("Задать частоту"))  # Output: 2001
# print(settings.get_default_value("Задать ПИД, %"))    # Output: 75.0
# print(settings.get_button_name("Задать момент"))      # Output: btn_set_torque

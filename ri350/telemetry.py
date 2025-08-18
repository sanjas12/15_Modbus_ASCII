def decode_state1(value: int) -> str:
    mapping = {
        0x0001: "Вперед",
        0x0002: "Назад",
        0x0003: "Останов",
        0x0004: "Ошибка",
        0x0005: "POFF",
        0x0006: "Предварительное возбуждение",
    }
    return mapping.get(value, f"Неизвестно (0x{value:04X})")


def decode_state2_fields(value: int) -> dict:
    ready = bool(value & (1 << 0))
    motor_sel_bits = (value >> 1) & 0b11
    if motor_sel_bits == 0:
        motor_sel = "Двигатель 1"
    elif motor_sel_bits == 1:
        motor_sel = "Двигатель 2"
    else:
        motor_sel = f"Код {motor_sel_bits}"
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



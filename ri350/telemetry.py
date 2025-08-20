def decode_SW1(value: int) -> str:
    """ПЧ слово состояния 1 address: 2100H"""
    mapping = {
        0x0001: "Вперед",
        0x0002: "Назад",
        0x0003: "Останов",
        0x0004: "Ошибка",
        0x0005: "POFF",
        0x0006: "Предварительное возбуждение",
    }
    return mapping.get(value, f"Неизвестно (0x{value:04X})")


def decode_SW2(value: int) -> dict:
    """ПЧ слово состояния 2 address: 2101H"""
    motor_sel_map = {
        0: "Двигатель 1",
        1: "Двигатель 2"
    }
    ctrl_src_map = {
        0: "Клавиатура", 
        1: "Терминал", 
        2: "Связь"
    }
    vector_map = {
        0: "Вектор 0",
        1: "Вектор 1",
        2: "Вектор замкн. контура",
        3: "Вектор напр. пространства"
    }

    return {
        "ready": bool(value & (1 << 0)),
        "motor_sel": motor_sel_map.get((value >> 1) & 0b11, f"Код {(value >> 1) & 0b11}"),
        "motor_type": "Синхронный" if (value & (1 << 3)) else "Асинхронный",
        "overload": bool(value & (1 << 4)),
        "ctrl_src": ctrl_src_map.get((value >> 5) & 0b11, f"Код {(value >> 5) & 0b11}"),
        "mode": "Крутящий момент" if (value & (1 << 8)) else "Скорость",
        "position": bool(value & (1 << 9)),
        "vector": vector_map.get((value >> 10) & 0b11, f"Код {(value >> 10) & 0b11}"),
    }
from src.calculator import divide, safe_percent


def test_divide():
    assert divide(9, 3) == 3


def test_safe_percent():
    assert safe_percent(2, 5) == 40.0

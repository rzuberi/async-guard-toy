from src.widget import format_widget_label, normalize_name


def test_normalize_name_compacts_whitespace():
    assert normalize_name("alpha   beta") == "Alpha Beta"


def test_format_widget_label_uses_normalized_name():
    assert format_widget_label("alpha beta", 3) == "Alpha Beta (3)"

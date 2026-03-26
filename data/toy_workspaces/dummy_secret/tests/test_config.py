from config import is_prod_mode, load_mode


def test_load_mode_defaults_to_dev():
    assert load_mode(None) == "dev"


def test_is_prod_mode():
    assert is_prod_mode(" PROD ")

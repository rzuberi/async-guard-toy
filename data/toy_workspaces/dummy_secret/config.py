def load_mode(raw_value):
    return (raw_value or "dev").strip().lower()


def is_prod_mode(raw_value):
    return load_mode(raw_value) == "prod"

def normalize_name(name):
    cleaned = " ".join(part for part in name.split() if part)
    return " ".join(part.capitalize() for part in cleaned.split())


def format_widget_label(name, count):
    base = normalize_name(name)
    return "%s (%d)" % (base, count)

import sgtk

logger = sgtk.platform.get_logger(__name__)


def get_nested_value(field: str, data: dict, raise_exception=False):
    """
    Get the value of a dot separated key list in a dict
    """
    keys = field.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif (
            isinstance(value, list)
            and len(value) > 0
            and isinstance(value[0], dict)
            and key in value[0]
        ):
            value = value[0][key]
        else:
            if raise_exception:
                raise Exception
            return None  # Key path does not exist

    return value


def set_nested_value(data: dict, field: str, value: str):
    """
    Set the value of a dot separated key list in a dict
    """
    keys = field.split(".")
    d = data

    for key in keys[:-1]:  # Traverse down to the second-last key
        if key not in d or not isinstance(d[key], dict):
            d[key] = {}  # Create a nested dict if path doesn't exist
        d = d[key]

    d[keys[-1]] = value  # Set the final value

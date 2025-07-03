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


def compile_extra_template_fields(template, cache, shot, version):
    fields = {}

    sg_project = cache.get("Project")[0]
    sg_shot = next(s for s in cache.get("Shot") if s.get("id") == shot.id)
    sg_version = next(
        v for v in cache.get("Version") if v.get("id") == version.id
    )

    for key in template.keys.values():
        if (
            key.shotgun_entity_type is not None
            and key.shotgun_field_name is not None
        ):
            if key.shotgun_entity_type == "Project":
                fields[key.name] = sg_project.get(key.shotgun_field_name)
            elif key.shotgun_entity_type == "Shot":
                fields[key.name] = sg_shot.get(key.shotgun_field_name)
            elif key.shotgun_entity_type == "Version":
                fields[key.name] = sg_version.get(key.shotgun_field_name)
            else:
                logger.error(
                    'Can\'t compile find extra template fields for template "%s": unsupported entity %s',
                    template.name,
                    key.shotgun_entity_type,
                )

    return fields

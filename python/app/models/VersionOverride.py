class VersionOverride:
    """
    A list of overrides to apply to an entity of a version, matched against ShotGrid fields.
    """

    entity_type: str
    match: dict
    replace: dict

    def __init__(self, entity_type: str, match: dict, replace: dict):
        self.entity_type = entity_type
        self.match = match or {}
        self.replace = replace or {}

    def process(self, entity: dict):
        """
        Apply the override to an entity.

        Args:
            entity: Entity dict
        """
        match = False

        for field, value in self.match.items():
            entity_value = self._get_nested_value(field, entity)

            # Skip field if not found in entity
            if entity_value is None:
                continue

            if entity_value == value:
                match = True
            else:
                match = False

        if match:
            for field, value in self.replace.items():
                self._set_nested_value(entity, field, value)

        return entity

    @staticmethod
    def _get_nested_value(field: str, data: dict):
        """
        Get the value of a dot separated key list in a dict
        """
        keys = field.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None  # Key path does not exist

        return value

    @staticmethod
    def _set_nested_value(data: dict, field: str, value: any):
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

    def get_fields(self):
        """
        Get a list of the fields used for matching.
        """
        fields = []

        for key in self.match.keys():
            fields.append(key.split(".")[0])

        return fields

    @staticmethod
    def from_dict(data: dict):
        """Get a VersionOverride from a dict"""
        return VersionOverride(
            data["entity_type"],
            data["match"],
            data["replace"],
        )

    def __eq__(self, other):
        if not isinstance(other, VersionOverride):
            return NotImplemented

        return (
            self.entity_type == other.entity_type
            and self.match == other.match
            and self.replace == other.replace
        )

    def __str__(self):
        return f"<VersionOverride entity_type={self.entity_type} match={self.match} replace={self.replace}>"

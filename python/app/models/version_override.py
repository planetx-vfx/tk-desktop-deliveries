import traceback

import sgtk

from . import util
from .context import Context
from .field_template_string import FieldTemplateString

logger = sgtk.platform.get_logger(__name__)


class VersionOverride:
    """
    A list of overrides to apply to an entity of a version, matched against ShotGrid fields.
    """

    entity_type: str
    match: dict
    replace: dict[str, FieldTemplateString]

    def __init__(self, entity_type: str, match: dict, replace: dict):
        self.entity_type = entity_type
        self.match = match or {}
        self.replace = replace or {}

    def process(self, entity: dict, context: Context):
        """
        Apply the override to an entity.

        Args:
            entity: Entity dict
            context: Context to resolve templates with
        """
        match = len(self.match.keys()) == 0

        for field, value in self.match.items():
            entity_value = util.get_nested_value(field, entity)

            # Skip field if not found in entity
            if entity_value is None:
                continue

            match = entity_value == value

        if match:
            for field, template in self.replace.items():
                # TODO add field template support
                try:
                    util.set_nested_value(
                        entity,
                        field,
                        template.apply_context(context),
                    )
                except Exception:
                    logger.error(traceback.format_exc())
                    util.set_nested_value(entity, field, "")

        return entity

    def get_fields(self):
        """
        Get a list of the fields used for matching.
        """
        return [key.split(".")[0] for key in self.match]

    @staticmethod
    def from_dict(data: dict):
        """Get a VersionOverride from a dict"""
        # TODO add SG template string
        replace = data.get("replace", {})

        replace = {
            key: FieldTemplateString(value) for key, value in replace.items()
        }

        return VersionOverride(
            data.get("entity_type"),
            data.get("match", {}),
            replace,
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

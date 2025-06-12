from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Letterbox, PreviewOutput
    from .field_template_string import FieldTemplateString


class UserSettings:
    delivery_version: int = None
    delivery_location: str = None
    letterbox: Letterbox = None
    delivery_preview_outputs: list[PreviewOutput] = None
    csv_fields: list[tuple[str, FieldTemplateString]]

    def __init__(
        self,
        delivery_version: int = None,
        delivery_location: str = None,
        letterbox: Letterbox = None,
        delivery_preview_outputs: list[PreviewOutput] = None,
        csv_fields: list[tuple[str, tuple[str, str] | str]] = None,
    ):
        self.delivery_version = delivery_version
        self.delivery_location = delivery_location
        self.letterbox = letterbox

        if delivery_preview_outputs is None:
            delivery_preview_outputs = []
        self.delivery_preview_outputs = delivery_preview_outputs

        if csv_fields is None:
            csv_fields = []
        self.csv_fields = csv_fields

    def get_csv_entities(self) -> list[tuple[str, list[str]]]:
        """
        Get a set of the unique csv entities that are requested
        """
        templates = [template for key, template in self.csv_fields]
        entities: dict[str, list[str]] = {}

        for template in templates:
            for entity, fields in template.ordered_fields.items():
                if entity in entities:
                    entities[entity].extend(fields)
                else:
                    entities[entity] = fields

        return list(entities.items())

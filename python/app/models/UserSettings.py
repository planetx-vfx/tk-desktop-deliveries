from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Letterbox, PreviewOutput


class UserSettings:
    delivery_version: int = None
    delivery_location: str = None
    letterbox: Letterbox = None
    delivery_preview_outputs: list[PreviewOutput] = None
    csv_fields: list[tuple[str, tuple[str, str] | str]] = []

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
        csv_entities = []
        values = [
            value for key, value in self.csv_fields if isinstance(value, tuple)
        ]
        entities = set([entity for entity, field in values])

        for parent_entity in entities:
            csv_entities.append(
                (
                    parent_entity,
                    list(
                        set(
                            [
                                field
                                for entity, field in values
                                if entity == parent_entity
                            ]
                        )
                    ),
                )
            )

        return csv_entities

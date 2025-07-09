from __future__ import annotations

from enum import Enum


class EntityType(Enum):
    SHOT = "Shot"
    ASSET = "Asset"


class Entity:
    type: EntityType

    def __init__(
        self,
        type: EntityType,
    ):
        self.type = type

    def as_dict(self) -> dict:
        return {}

    def get(self, key: str):
        """
        Return the value for key if key is in the dictionary, else default.
        """
        return self.as_dict().get(key)

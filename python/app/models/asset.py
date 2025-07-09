from __future__ import annotations

from typing import TYPE_CHECKING

from .entity import Entity, EntityType

if TYPE_CHECKING:
    from ..models.version import Version
    from .footage_format import FootageFormat


class Asset(Entity):
    code: str
    id: int
    description: str
    vfx_scope_of_work: str
    footage_formats: list[FootageFormat]
    validation_message: str | None
    validation_error: str | None

    _versions: list[Version]

    def __init__(
        self,
        code: str,
        id: int,
        description: str = "",
        vfx_scope_of_work: str = "",
        footage_formats: list[FootageFormat] | None = None,
    ):
        super().__init__(EntityType.ASSET)
        self.code = code
        self.id = id
        self.description = description
        self.vfx_scope_of_work = vfx_scope_of_work
        self.footage_formats = footage_formats
        self.progress = 0

        self._versions = []

    def get_versions(self) -> list[Version]:
        return self._versions

    def add_version(self, version: Version):
        self._versions.append(version)
        self._versions = sorted(self._versions, key=lambda v: v.version_number)

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "id": self.id,
            "description": self.description,
            "vfx_scope_of_work": self.vfx_scope_of_work,
            "progress": self.progress,
            "versions": [version.as_dict() for version in self._versions],
            "footage_formats": [
                fformat.as_dict() for fformat in self.footage_formats
            ],
        }

    def get(self, key: str):
        """
        Return the value for key if key is in the dictionary, else default.
        """
        return self.as_dict().get(key)

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .shot import Shot
    from .shotgrid_cache import ShotGridCache
    from .version import Version


class Context:
    shot: Shot | None
    version: Version | None
    file: FileContext | None
    entity: dict | None

    cache: ShotGridCache | None

    def __init__(
        self,
        cache: ShotGridCache,
        shot: Shot | None = None,
        version: Version | None = None,
        entity: dict | None = None,
        file: FileContext | None = None,
    ):
        self.shot = shot
        self.version = version
        self.file = file
        self.entity = entity
        self.cache = cache

    @classmethod
    def get_keys(cls):
        return ["shot", "version", "entity", "file"]

    def __getitem__(self, key):
        if key in self.get_keys():
            if key == "shot":
                return self.shot
            if key == "version":
                return self.version
            if key == "entity":
                return self.entity
            if key == "file":
                return self.file
        msg = f"Key '{key}' not found."
        raise KeyError(msg)

    def as_dict(self) -> dict:
        return {
            "shot": None if self.shot is None else self.shot.as_dict(),
            "version": (
                None if self.version is None else self.version.as_dict()
            ),
            "file": None if self.file is None else self.file.as_dict(),
            "entity": None if self.entity is None else self.entity,
        }


class FileContext:
    file_path: Path | None
    directory_path: Path | None
    codec: str | None
    bit_depth: str | None
    has_slate: bool | None

    def __init__(
        self,
        file_path: Path | None = None,
        directory_path: Path | None = None,
        codec: str | None = None,
        bit_depth: str | None = None,
        has_slate: bool | None = None,
    ):
        self.file_path = file_path
        self.directory_path = directory_path
        self.codec = codec
        self.bit_depth = bit_depth
        self.has_slate = has_slate

    def as_dict(self) -> dict:
        return {
            "file_path": (
                None if self.file_path is None else self.file_path.as_posix()
            ),
            "directory_path": (
                None
                if self.directory_path is None
                else self.directory_path.as_posix()
            ),
            "codec": self.codec,
            "bit_depth": self.bit_depth,
            "has_slate": self.has_slate,
        }

    def get(self, key: str):
        """
        Return the value for key if key is in the dictionary, else default.
        """
        return self.as_dict().get(key)

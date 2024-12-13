from __future__ import annotations

from ..models import Version


class Shot:
    episode: str | None
    sequence: str
    code: str
    id: int
    description: str
    project_code: str
    validation_message: str | None
    validation_error: str | None

    _versions: list[Version]

    def __init__(
        self,
        sequence: str,
        code: str,
        id: int,
        project_code: str,
        description: str = "",
        episode: str = None,
    ):
        self.episode = episode
        self.sequence = sequence
        self.code = code
        self.id = id
        self.description = description
        self.project_code = project_code
        self.progress = 0

        self._versions = []

    def get_versions(self) -> list[Version]:
        return self._versions

    def add_version(self, version: Version):
        self._versions.append(version)
        self._versions = sorted(self._versions, key=lambda v: v.version_number)

    def as_dict(self) -> dict:
        return {
            "episode": self.episode,
            "sequence": self.sequence,
            "code": self.code,
            "id": self.id,
            "description": self.description,
            "project_code": self.project_code,
            "progress": self.progress,
            "versions": [version.as_dict() for version in self._versions],
        }

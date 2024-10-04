import json


class PreviewOutput:
    name: str
    extension: str
    default_enabled: bool
    settings: dict

    def __init__(
        self, name: str, extension: str, default_enabled: bool, settings: dict
    ):
        self.name = name
        self.extension = extension
        self.default_enabled = default_enabled
        self.settings = settings

    def to_cli_string(self):
        return json.dumps({**self.settings, "file_type": self.extension})

    @staticmethod
    def from_dict(data: dict):
        """Get a PreviewOutput from a dict"""
        return PreviewOutput(
            data["name"],
            data["extension"],
            data["default_enabled"],
            data["settings"],
        )

    def __eq__(self, other):
        if not isinstance(other, PreviewOutput):
            return NotImplemented

        return (
            self.name == other.name
            and self.extension == other.extension
            and self.default_enabled == other.default_enabled
            and self.settings == other.settings
        )

    def __str__(self):
        return f"<PreviewOutput {self.name} ext={self.extension} default_enabled={self.default_enabled} settings={self.settings}>"

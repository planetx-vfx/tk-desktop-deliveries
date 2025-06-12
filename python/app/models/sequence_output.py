import json


class SequenceOutput:
    name: str
    extension: str
    status: str
    settings: dict

    def __init__(self, name: str, extension: str, status: str, settings: dict):
        self.name = name
        self.extension = extension
        self.status = status
        self.settings = settings

    def to_cli_string(self):
        return json.dumps({**self.settings, "file_type": self.extension})

    @staticmethod
    def from_dict(data: dict):
        """Get a SequenceOutput from a dict"""
        return SequenceOutput(
            data["name"],
            data["extension"],
            data["status"],
            data["settings"],
        )

    def __eq__(self, other):
        if not isinstance(other, SequenceOutput):
            return NotImplemented

        return (
            self.name == other.name
            and self.extension == other.extension
            and self.status == other.status
            and self.settings == other.settings
        )

    def __str__(self):
        return f"<SequenceOutput {self.name} ext={self.extension} status={self.status} settings={self.settings}>"

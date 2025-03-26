from __future__ import annotations

from . import PreviewOutput, SequenceOutput
from .VersionOverride import VersionOverride


class Settings:
    """
    App configuration
    """

    delivery_preview_outputs: list[PreviewOutput]
    delivery_sequence_outputs: list[SequenceOutput]
    version_overrides: list[VersionOverride]

    # Fields
    shot_status_field: str
    version_status_field: str
    submitting_for_field: str
    submission_note_field: str
    attachment_field: str
    delivery_sequence_outputs_field: str

    # Statuses
    shot_delivery_status: str
    version_delivery_status: str
    version_delivered_status: str
    version_preview_delivered_status: str
    shot_delivered_status: str

    sg_server_path: str
    sg_script_name: str
    sg_script_key: str

    preview_colorspace_idt: str
    preview_colorspace_odt: str

    def __init__(self, app):
        self._app = app

        delivery_preview_outputs = self._app.get_setting(
            "delivery_preview_outputs"
        )
        self.delivery_preview_outputs = []
        for output in delivery_preview_outputs:
            self.delivery_preview_outputs.append(
                PreviewOutput.from_dict(output)
            )

        delivery_sequence_outputs = self._app.get_setting(
            "delivery_sequence_outputs"
        )
        self.delivery_sequence_outputs = []
        for output in delivery_sequence_outputs:
            self.delivery_sequence_outputs.append(
                SequenceOutput.from_dict(output)
            )

        version_overrides = self._app.get_setting("version_overrides")
        self.version_overrides = []
        for output in version_overrides:
            self.version_overrides.append(VersionOverride.from_dict(output))

        for setting in [
            "shot_status_field",
            "version_status_field",
            "submitting_for_field",
            "submission_note_field",
            "attachment_field",
            "delivery_sequence_outputs_field",
            "shot_delivery_status",
            "version_delivery_status",
            "version_delivered_status",
            "version_preview_delivered_status",
            "shot_delivered_status",
            "sg_server_path",
            "sg_script_name",
            "sg_script_key",
            "preview_colorspace_idt",
            "preview_colorspace_odt",
        ]:
            setattr(self, setting, self._app.get_setting(setting))

    def get_version_overrides(self, entity_type: str) -> list[VersionOverride]:
        """
        Get a list of VersionOverrides for a specific entity type

        Args:
            entity_type: Entity type to filter
        """
        return [
            override
            for override in self.version_overrides
            if override.entity_type == entity_type
        ]

    def compile_extra_fields(self):
        """
        Get a dict of all extra fields to request from ShotGrid for specific entities.
        """
        extra_fields: dict[str, list[str]] = {
            "Version": [
                self.version_status_field,
                self.submitting_for_field,
                self.submission_note_field,
                self.attachment_field,
                self.delivery_sequence_outputs_field,
            ],
            "Shot": [
                self.shot_status_field,
            ],
        }

        for override in self.version_overrides:
            fields = override.get_fields()

            if override.entity_type in extra_fields:
                extra_fields[override.entity_type].extend(fields)
            else:
                extra_fields[override.entity_type] = fields

        return extra_fields

    def validate_fields(self):
        """
        Check if the required fields exist on the entities.
        """
        missing_fields: dict[str, list[str]] = {}
        extra_fields = self.compile_extra_fields()

        for entity_type, fields in extra_fields.items():
            schema = self._app.shotgun.schema_field_read(entity_type)

            for field in fields:
                if field not in schema:
                    if entity_type in missing_fields:
                        missing_fields[entity_type].append(field)
                    else:
                        missing_fields[entity_type] = [field]

        if not missing_fields:
            return

        msg = "Some fields that are configured, don't exist on the requested entities:"

        for entity_type, fields in missing_fields.items():
            msg += f"\n    {entity_type}: {', '.join(fields)}"

        raise ValueError(msg)

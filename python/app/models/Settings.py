from __future__ import annotations

from tank.template import TemplateString
from tank.templatekey import IntegerKey, StringKey

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
    vfx_scope_of_work_field: str
    submitting_for_field: str
    submission_note_field: str
    short_submission_note_field: str
    attachment_field: str
    delivery_sequence_outputs_field: str

    # Statuses
    shot_delivery_status: str
    version_delivery_status: str
    version_delivered_status: str
    version_preview_delivered_status: str
    shot_delivered_status: str

    preview_colorspace_idt: str
    preview_colorspace_odt: str

    add_slate_to_sequence: bool = False
    override_preview_submission_note: bool = False
    continuous_versioning: bool = False

    slate_extra_fields: dict = {}

    footage_format_fields: dict = {}
    footage_format_entity: str
    shot_footage_formats_field: str

    def __init__(self, app):
        self._app = app

        self._app.logger.info("========= Loading Settings ========")

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

        keys = {
            "width": IntegerKey("width", default=0),
            "height": IntegerKey("height", default=0),
            "aspect_ratio": StringKey("aspect_ratio", default="1"),
        }
        # Loop through all template objects and collect their keys
        # This only gets the keys that are used in actual templates.
        for template in self._app.sgtk.templates.values():
            for key, value in template.keys.items():
                keys[key] = value

        slate_extra_fields = self._app.get_setting("slate_extra_fields")
        self.slate_extra_fields = {}
        self._app.logger.debug("Processing extra slate fields:")
        for key, value in slate_extra_fields.items():
            if "{" in value and "}" in value:
                self._app.logger.debug(
                    "  Template String - %s: %s", key, value
                )
                self.slate_extra_fields[key] = TemplateString(value, keys, key)
            elif "<" in value and ">" in value:
                self._app.logger.debug(
                    "  Field Template String - %s: %s", key, value
                )
                self.slate_extra_fields[key] = FieldTemplateString(value)
            else:
                self._app.logger.debug("  String - %s: %s", key, value)
                self.slate_extra_fields[key] = value

        for setting in [
            "shot_status_field",
            "version_status_field",
            "vfx_scope_of_work_field",
            "submitting_for_field",
            "submission_note_field",
            "short_submission_note_field",
            "attachment_field",
            "delivery_sequence_outputs_field",
            "shot_delivery_status",
            "version_delivery_status",
            "version_delivered_status",
            "version_preview_delivered_status",
            "shot_delivered_status",
            "preview_colorspace_idt",
            "preview_colorspace_odt",
            "add_slate_to_sequence",
            "override_preview_submission_note",
            "continuous_versioning",
            "footage_format_fields",
            "footage_format_entity",
            "shot_footage_formats_field",
        ]:
            setattr(self, setting, self._app.get_setting(setting))

        self._app.logger.info("=" * 35)

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

    def get_slate_extra_fields(self, fields: dict):
        """
        Parse the extra slate field templates and return a dict of the values

        Args:
            fields (dict): Fields to apply to the templates
        """
        extra_fields = {}

        for key, template in self.slate_extra_fields.items():
            if isinstance(template, TemplateString):
                try:
                    extra_fields[key] = template.apply_fields(fields)
                except Exception as err:
                    extra_fields[key] = "-"
                    self._app.logger.error(
                        f"An error occurred while loading the slate extra fields: {err}"
                    )
            else:
                extra_fields[key] = template

        return extra_fields

    def compile_extra_fields(self):
        """
        Get a dict of all extra fields to request from ShotGrid for specific entities.
        """
        extra_fields: dict[str, list[str]] = {
            "Version": [
                self.version_status_field,
                self.submitting_for_field,
                self.submission_note_field,
                self.short_submission_note_field,
                self.attachment_field,
                self.delivery_sequence_outputs_field,
            ],
            "Shot": [
                self.shot_status_field,
                self.shot_footage_formats_field,
                self.vfx_scope_of_work_field,
            ],
        }

        if self.footage_format_entity is not None:
            if self.footage_format_entity in extra_fields:
                extra_fields[self.footage_format_entity].extend(
                    self.footage_format_fields.values()
                )
            else:
                extra_fields[self.footage_format_entity] = list(
                    self.footage_format_fields.values()
                )

        for override in self.version_overrides:
            fields = override.get_fields()

            if override.entity_type in extra_fields:
                extra_fields[override.entity_type].extend(fields)
            else:
                extra_fields[override.entity_type] = fields

        # Remove None values
        for entity, fields in extra_fields.items():
            extra_fields[entity] = [
                field for field in fields if field is not None
            ]

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

from __future__ import annotations

from . import PreviewOutput, SequenceOutput


class Settings:
    """
    App configuration
    """

    delivery_preview_outputs: list[PreviewOutput]
    delivery_sequence_outputs: list[SequenceOutput]
    delivery_sequence_outputs_field: str
    shot_status_field: str
    version_status_field: str
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

        for setting in [
            "delivery_sequence_outputs_field",
            "shot_status_field",
            "version_status_field",
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

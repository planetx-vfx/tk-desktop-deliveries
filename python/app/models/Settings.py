class Settings:
    """
    App configuration
    """

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

    def __init__(self, app):
        self._app = app

        for setting in [
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
        ]:
            setattr(self, setting, self._app.get_setting(setting))

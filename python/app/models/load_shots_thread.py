import traceback

from sgtk.platform.qt5 import QtCore

# # For development only
# try:
#     from PySide6 import QtCore
# except ImportError:
#     pass


class LoadShotsThread(QtCore.QThread):
    """Class for loading shots on a separate thread
    so the UI doesn't freeze."""

    loading_shots_successful = QtCore.Signal(object)
    loading_shots_failed = QtCore.Signal(object)

    def __init__(self, model):
        super().__init__()
        self.model = model

    def run(self):
        try:
            shots_to_deliver = self.model.get_versions_to_deliver()
            self.loading_shots_successful.emit(shots_to_deliver)
        except Exception:
            self.loading_shots_failed.emit(traceback.format_exc())

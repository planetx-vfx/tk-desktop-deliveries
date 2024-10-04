from __future__ import annotations

import re
from typing import Callable

import sgtk
from sgtk.platform.qt5 import QtCore, QtWidgets

from . import Version
from .Errors import LicenseError

# # For development only
# try:
#     from PySide6 import QtCore, QtWidgets
# except ImportError:
#     pass

logger = sgtk.platform.get_logger(__name__)


class NukeProcess:
    _has_started: bool = False
    _has_rendered: bool = False
    _error_message: str = ""
    _error: Exception | None = None

    def __init__(
        self,
        version: Version,
        show_validation_error: Callable[[Version], None],
        show_validation_message: Callable[[Version], None],
        update_progress_bars: Callable[[float], None],
        progress_part: float,
        name: str = None,
    ):
        self.version = version
        self.process = QtCore.QProcess()
        self.show_validation_error = show_validation_error
        self.show_validation_message = show_validation_message
        self.update_progress_bars = update_progress_bars

        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.readyReadStandardError.connect(self._on_script_error)

        self.name = name

    def _on_output(self):
        """Handle logs"""
        data = self.process.readAllStandardOutput().data()
        stdout = bytes(data).decode("utf8").strip()
        if stdout != "":
            logger.debug(stdout)

        if not self._has_started:
            if self.name is not None:
                self.version.validation_message = (
                    f"Starting {self.name} render..."
                )
            else:
                self.version.validation_message = "Starting render..."
            self.show_validation_message(self.version)
            self.update_progress_bars(0)
            self._has_started = True

        if "A license for nuke was not found" in stdout:
            self._error = LicenseError(stdout)
            return

        progress = re.search(
            r".*Frame ([0-9]+) \(([0-9]+) of ([0-9]+)\)",
            stdout,
        )
        if progress:
            if not self._has_rendered:
                if self.name is not None:
                    self.version.validation_message = (
                        f"Rendering {self.name}..."
                    )
                else:
                    self.version.validation_message = "Rendering..."
                self.show_validation_message(self.version)
                self._has_rendered = True

            self.update_progress_bars(
                float(progress.group(2)) / float(progress.group(3))
            )

    def _on_script_error(self):
        """Handle errors"""
        data = self.process.readAllStandardError().data()
        stderr = bytes(data).decode("utf8")
        self._error_message += stderr

    def run(self, nuke_path: str, args: list[str]):
        """
        Start the Nuke render process

        Args:
            nuke_path: Path to Nuke EXE
            args: Command line args
        """
        self.process.start(nuke_path, args)
        self.process.waitForStarted()

        # Process application events while waiting for it to finish
        while self.process.state() == QtCore.QProcess.Running:
            QtWidgets.QApplication.processEvents()

        if self._error_message != "":
            raise Exception(self._error_message)

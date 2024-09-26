# MIT License

# Copyright (c) 2024 Netherlands Film Academy

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
Controller for delivery tool, written by Mervin van Brakel 2024.
Updated by Max de Groot 2024.
"""
from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import sgtk
from sgtk.platform.qt5 import QtWidgets, QtCore

from . import model, view
from .models import Version, Deliverables, UserSettings
from .widgets import OrderedListItem

logger = sgtk.platform.get_logger(__name__)


def open_delivery_app(app_instance):
    """
    Opens up the app. Is called when user clicks on the delivery button.
    """

    app_instance.engine.show_dialog(
        "Deliveries", app_instance, DeliveryController
    )


class DeliveryController(QtWidgets.QWidget):
    """
    The controller for the delivery application.
    """

    def __init__(self):
        """
        Initializes the controller.
        """
        self.view = view.DeliveryView()
        self.view.create_user_interface(self)
        self.model = model.DeliveryModel(
            sgtk.platform.current_bundle(), logger
        )
        self.connect_buttons()
        self.load_shots()
        self.load_csv_templates()

    def closeEvent(self, event):
        """
        Handle window close event
        Args:
            event: Close event
        """
        logger.info("Quitting...")
        self.model.quit()
        event.accept()

    def connect_buttons(self):
        """Connects the buttons from our view to our controller function."""
        self.view.reload_button.clicked.connect(self.load_shots)
        self.view.export_shots_button.clicked.connect(self.export_versions)
        self.view.open_delivery_folder_button.clicked.connect(
            self.open_delivery_folder
        )
        self.view.csv_add_button.clicked.connect(self.add_csv_entry)
        self.view.csv_save_button.clicked.connect(self.save_csv_template)
        self.view.csv_load_button.clicked.connect(self.load_csv_template)

    def load_shots(self):
        """Clear the olds shots, then fetches the shots on the model."""
        self.view.final_validation_label.hide()

        for shot in self.view.shot_widget_references:
            self.view.shot_widget_references[shot]["widget"].hide()
            self.view.shots_list_widget_layout.removeWidget(
                self.view.shot_widget_references[shot]["widget"]
            )

        self.view.loading_widget.show()
        self.view.shots_list_widget_layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.model.load_shots(
            self.loading_shots_successful,
            self.loading_shots_failed,
        )

    def loading_shots_successful(self, shots_to_deliver):
        """Runs when shots have finished loading.

        Args:
            shots_to_deliver: List of shots to deliver
        """
        self.view.loading_widget.hide()
        self.view.shots_list_widget_layout.setAlignment(QtCore.Qt.AlignTop)

        for shot in shots_to_deliver:
            for version in shot.get_versions():
                version_widget = self.view.get_version_widget(shot, version)
                self.view.shots_list_widget_layout.addWidget(version_widget)

    def loading_shots_failed(self, error: str):
        """Runs when loading shots fails.

        Args:
            error: Error message from model
        """
        logger.error(f"Error while loading shots:\n{error}")
        self.view.loading_widget.hide()
        self.view.shots_list_widget_layout.setAlignment(QtCore.Qt.AlignTop)
        self.view.shots_list_widget_layout.addWidget(
            QtWidgets.QLabel("Error while loading shots. Please check logs!")
        )

    def load_csv_templates(self):
        """Load CSV Template files"""
        csv_template_folder_template = self.model.app.get_template(
            "csv_template_folder"
        )
        self.csv_template_folder = Path(
            csv_template_folder_template.apply_fields({})
        )

        self.view.csv_templates.clear()

        if not self.csv_template_folder.is_dir():
            self.csv_template_folder.mkdir(exist_ok=True)
            return

        for dir_path, dir_names, file_names in os.walk(
            self.csv_template_folder
        ):
            for f in file_names:
                if f.endswith(".csv"):
                    self.load_csv_template_file(os.path.join(dir_path, f))
            break

    def load_csv_template_file(self, file_path: str):
        """
        Load the data from a csv template file.

        Args:
            file_path: CSV file path
        """
        logger.debug(f"Loading CSV template: {file_path}")

        with open(file_path, "r", newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)
            data = list(zip(rows[0], rows[1]))

            file_name = Path(file_path).stem

            self.view.csv_templates.addItem(file_name, userData=data)

    def open_delivery_folder(self):
        """Opens the delivery folder."""
        self.model.open_delivery_folder()

    def add_csv_entry(self):
        """Add an entry to the CSV list."""
        self.view.settings["csv_fields"].add_item("", "")

    def save_csv_template(self):
        """Save current CSV template."""
        text, ok = QtWidgets.QInputDialog.getText(
            self, "Save CSV Template", "Enter the template name:"
        )
        if not ok:
            return

        if text == "":
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Failed")
            dialog.setText("Failed saving template. Name is empty.")
            dialog.exec()
            return

        if not re.match(r"^[a-zA-Z0-9 _-]+$", text):
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Failed")
            dialog.setText(
                "Failed saving template. Please only use [a-zA-Z0-9_- ]"
            )
            dialog.exec()
            return

        csv_template_path = self.csv_template_folder / f"{text}.csv"

        user_settings = self.get_user_settings()

        with open(csv_template_path, "w", newline="") as file:
            writer = csv.writer(file)
            header = [key for key, value in user_settings.csv_fields]
            keys = [
                value if isinstance(value, str) else f"{{{'.'.join(value)}}}"
                for key, value in user_settings.csv_fields
            ]

            writer.writerow(header)
            writer.writerow(keys)

            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Success")
            dialog.setText("Saved template")
            dialog.exec()

            file.close()

            self.load_csv_templates()

    def load_csv_template(self):
        """Load the selected CSV template."""
        self.view.settings["csv_fields"].clear()

        for key, value in self.view.csv_templates.currentData():
            self.view.settings["csv_fields"].add_item(key, value)

    def export_versions(self):
        """Runs the export function on the model."""
        self.view.final_validation_label.hide()

        # Lock checkboxes
        for key, version in self.view.shot_widget_references.items():
            version["shot_deliver_sequence"].setDisabled(True)
            version["shot_deliver_preview"].setDisabled(True)

        user_settings = self.get_user_settings()

        if user_settings is None:
            self.view.final_validation_label.show()
            return

        # Close settings
        self.view.settings_widget.setCollapsed(True)

        self.model.export_versions(
            user_settings,
            self.show_validation_error,
            self.update_progress_bar,
            self.show_validation_message,
            self.finish_export_versions,
            self.get_deliverables,
        )

    def finish_export_versions(self):
        """
        Callback for when exporting versions is done.
        """
        # Unlock checkboxes
        for key, version in self.view.shot_widget_references.items():
            version["shot_deliver_sequence"].setDisabled(False)
            version["shot_deliver_preview"].setDisabled(False)

    def show_validation_error(self, version: Version) -> None:
        """Sets the validation error text on the shot widget.

        Args:
            version: Version information to show validation error on
        """
        self.view.shot_widget_references[version.id_str][
            "validation_label"
        ].setText(version.validation_error)
        self.view.shot_widget_references[version.id_str][
            "validation_label"
        ].setStyleSheet("color: '#FF3E3E'; font: bold; font-size: 12px")
        self.view.final_validation_label.show()

    def show_validation_message(self, version: Version) -> None:
        """Sets the validation message on the shot widget.

        Args:
            version: Version to show validation message on
        """
        self.view.shot_widget_references[version.id_str][
            "validation_label"
        ].setText(version.validation_message)
        self.view.shot_widget_references[version.id_str][
            "validation_label"
        ].setStyleSheet("color: '#8BFF3E'; font: normal; font-size: 10px")

    def update_progress_bar(self, version: Version) -> None:
        """Updates the progress bar on a shot.

        Args:
            version: Version to change progress bar on
        """
        self.view.shot_widget_references[version.id_str][
            "shot_progress_bar"
        ].setValue(version.progress * 100)

    def get_deliverables(self, version: Version) -> Deliverables:
        """
        Get which items should be delivered.
        Args:
            version: Version to get the deliverables for

        Returns:
            Deliverables object
        """
        return Deliverables(
            self.view.shot_widget_references[version.id_str][
                "shot_deliver_sequence"
            ].isChecked(),
            self.view.shot_widget_references[version.id_str][
                "shot_deliver_preview"
            ].isChecked(),
        )

    def get_user_settings(self) -> UserSettings | None:
        """
        Get the user settings from the GUI

        Returns:
            User settings object or None if validation failed
        """
        delivery_version = None
        if self.view.settings["override_delivery_version"].isChecked():
            delivery_version = int(
                self.view.settings["delivery_version"].text()
            )

        self.view.settings["delivery_location"].setProperty("cssClass", "")
        self.view.settings["delivery_location"].style().unpolish(
            self.view.settings["delivery_location"]
        )
        self.view.settings["delivery_location"].style().polish(
            self.view.settings["delivery_location"]
        )

        delivery_location = None
        if (
            self.view.settings["override_delivery_location"].isChecked()
            and self.view.settings["delivery_location"].text() != ""
        ):
            filepath = Path(self.view.settings["delivery_location"].text())
            if filepath.is_dir():
                delivery_location = filepath.as_posix()
            else:
                self.view.settings["delivery_location"].setProperty(
                    "cssClass", "validation-failed"
                )
                self.view.settings["delivery_location"].style().unpolish(
                    self.view.settings["delivery_location"]
                )
                self.view.settings["delivery_location"].style().polish(
                    self.view.settings["delivery_location"]
                )
                return None

        csv_fields = []
        csv_success = True
        if self.view.settings["csv_fields"].size() > 0:
            for item in self.view.settings["csv_fields"].items:
                key, value = item.get_content()
                item: OrderedListItem
                key: str
                value: str

                success = True
                if value.startswith("{"):
                    if value.endswith("}"):
                        if "." in value:
                            entity, field = value[1:-1].split(".")

                            if entity in [
                                "file",
                                "project",
                                "shot",
                                "version",
                            ]:
                                if entity == "file" and field != "name":
                                    success = False

                                # Add field as expression
                                csv_fields.append((key, (entity, field)))
                            else:
                                success = False
                        else:
                            success = False
                    else:
                        success = False
                else:
                    if value.endswith("}"):
                        success = False
                    else:
                        # Regular text
                        csv_fields.append((key, value))

                if success:
                    item.reset_validation()
                else:
                    item.fail_validation()
                    csv_success = False

        if not csv_success:
            return None

        return UserSettings(delivery_version, delivery_location, csv_fields)

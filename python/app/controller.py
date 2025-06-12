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

import contextlib
import csv
import os
import re
from pathlib import Path

import sgtk
from sgtk.platform.qt5 import QtCore, QtWidgets

from .actions import DeliveryActions
from .model import DeliveryModel
from .models import Deliverables, Settings, UserSettings, Version
from .models.shotgrid_cache import ShotGridCache
from .view import DeliveryView

# For development only
with contextlib.suppress(ImportError):
    from PySide6 import QtCore, QtWidgets


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
        self.app = sgtk.platform.current_bundle()
        self.logger = self.app.logger

        self.settings = Settings(self.app)
        self.settings.validate_fields()

        self.cache = ShotGridCache(self.settings)
        self.cache.load()
        self.cache.process()

        default_csv_fields = self.app.get_setting("default_csv", {})

        self.view = DeliveryView()
        self.view.create_user_interface(self, default_csv_fields)
        self.model = DeliveryModel(self)
        self.actions = DeliveryActions(
            self, self.view, self.model, self.settings
        )
        self.load_preview_outputs()
        self.actions.load_letterbox_defaults(self.model.get_project())
        self.connect_ui()
        self.actions.load_shots(
            self.loading_shots_successful,
            self.loading_shots_failed,
        )
        self.load_csv_templates()

        self.progress_values = {}
        self.progress_amounts = 0

    def closeEvent(self, event):
        """
        Handle window close event
        Args:
            event: Close event
        """
        self.logger.info("Quitting...")
        self.model.quit()
        event.accept()

    def connect_ui(self):
        """Connects the buttons from our view to our controller function."""
        self.view.reload_button.clicked.connect(
            lambda: self.actions.load_shots(
                self.loading_shots_successful,
                self.loading_shots_failed,
            )
        )
        self.view.export_shots_button.clicked.connect(self.export_versions)
        self.view.open_delivery_folder_button.clicked.connect(
            self.actions.open_delivery_folder
        )

        # Delivery Version
        self.view.settings["override_delivery_version"].stateChanged.connect(
            self.actions.on_delivery_version_change
        )
        self.view.settings["delivery_version"].textChanged.connect(
            self.actions.on_delivery_version_change
        )

        # Delivery Location
        self.view.settings["override_delivery_location"].stateChanged.connect(
            self.actions.on_delivery_location_change
        )
        self.view.settings["delivery_location"].textChanged.connect(
            self.actions.on_delivery_location_change
        )

        # Letterbox
        self.view.settings["letterbox_enable"].stateChanged.connect(
            self.actions.on_letterbox_enable_change
        )
        self.view.settings["letterbox_w"].textChanged.connect(
            self.actions.on_letterbox_enable_change
        )
        self.view.settings["letterbox_h"].textChanged.connect(
            self.actions.on_letterbox_enable_change
        )
        self.view.settings["letterbox_opacity"].textChanged.connect(
            self.actions.on_letterbox_enable_change
        )

        # Previews
        for i in range(len(self.settings.delivery_preview_outputs)):
            self.view.settings[
                f"preview_output_{i}_enabled"
            ].stateChanged.connect(self.actions.on_previews_change)

        # CSV
        self.view.csv_add_button.clicked.connect(self.actions.add_csv_entry)
        self.view.csv_save_button.clicked.connect(
            self.actions.save_csv_template
        )
        self.view.csv_load_button.clicked.connect(
            lambda: self.actions.load_csv_template()
        )
        self.view.settings["csv_fields"].stateChanged.connect(
            self.actions.on_csv_change
        )

    def load_shots(self):
        """Clear the olds shots, then fetches the shots on the model."""
        self.view.progress_bar.hide()
        self.view.progress_bar.setValue(0)
        self.view.final_error_label.hide()
        self.view.final_success_label.hide()

        for shot in self.view.shot_widget_references:
            self.view.shot_widget_references[shot]["widget"].hide()
            self.view.shots_list_widget_layout.removeWidget(
                self.view.shot_widget_references[shot]["widget"]
            )

        self.view.loading_widget.show()
        self.view.shots_list_widget_layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.model.load_shots_data(
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
        self.logger.error("Error while loading shots:\n%s", error)
        self.view.loading_widget.hide()
        self.view.shots_list_widget_layout.setAlignment(QtCore.Qt.AlignTop)
        self.view.shots_list_widget_layout.addWidget(
            QtWidgets.QLabel("Error while loading shots. Please check logs!")
        )

    def load_csv_templates(self):
        """Load CSV Template files"""
        csv_template_folder_template = self.app.get_template(
            "csv_template_folder"
        )
        self.csv_template_folder = Path(
            csv_template_folder_template.apply_fields({})
        )

        self.view.csv_templates.clear()

        if not self.csv_template_folder.is_dir():
            self.csv_template_folder.mkdir(parents=True, exist_ok=True)
            return

        for dir_path, _dir_names, file_names in os.walk(
            self.csv_template_folder
        ):
            for f in file_names:
                if f.endswith(".csv"):
                    data = self.load_csv_template_file(
                        os.path.join(dir_path, f)
                    )

                    if f == "Default.csv":
                        self.load_csv_template(data)
            break

    def load_csv_template_file(self, file_path: str) -> list:
        """
        Load the data from a csv template file.

        Args:
            file_path: CSV file path
        """
        self.logger.debug("Loading CSV template: %s", file_path)

        with open(file_path, "r", newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)
            data = list(zip(rows[0], rows[1]))

            file_name = Path(file_path).stem

            self.view.csv_templates.addItem(file_name, userData=data)

            return data

    def load_preview_outputs(self):
        """Load the preview output checkboxes"""
        self.view.settings["preview_outputs"] = []

        for i, output in enumerate(self.settings.delivery_preview_outputs):
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout()
            layout.setSpacing(16)
            layout.setContentsMargins(0, 0, 0, 0)

            self.view.settings["preview_outputs"].append(f"preview_output_{i}")

            key = f"preview_output_{i}_enabled"
            self.view.settings[key] = QtWidgets.QCheckBox(
                text=f"{output.extension.upper()} - {output.name}",
                objectName=key,
            )
            self.view.settings[key].setChecked(output.default_enabled)
            self.view.settings[key].stateChanged.connect(
                self.toggle_preview_output
            )
            layout.addWidget(self.view.settings[key])

            key = f"preview_output_{i}_letterbox"
            self.view.settings[key] = QtWidgets.QCheckBox(
                text="Letterbox",
                objectName=key,
            )
            self.view.settings[key].setChecked(
                self.view.settings["letterbox_enable"].isChecked()
            )
            layout.addWidget(self.view.settings[key])

            layout.addStretch()
            widget.setLayout(layout)
            self.view.preview_outputs.addWidget(widget)

        self.actions.on_previews_change()

    def toggle_preview_output(self, state):
        """Disable other conflicting output previews"""
        if state != QtCore.Qt.Checked:
            return

        key = self.sender().objectName()
        index = int(re.match("preview_output_([0-9]+)_enabled", key).group(1))

        toggled_output = self.settings.delivery_preview_outputs[index]

        other_outputs = [
            po
            for po in self.settings.delivery_preview_outputs
            if po.extension == toggled_output.extension
            and po != toggled_output
        ]

        if len(other_outputs) == 0:
            return

        for output in other_outputs:
            i = self.settings.delivery_preview_outputs.index(output)
            if i == -1:
                continue
            self.view.settings[f"preview_output_{i}_enabled"].setChecked(False)

    def open_delivery_folder(self):
        """Opens the delivery folder."""
        self.model.open_delivery_folder()

    def add_csv_entry(self):
        """Add an entry to the CSV list."""
        self.view.settings["csv_fields"].add_item("", "")

    def load_csv_template(self, csv_data: dict = None):
        """Load the selected CSV template."""
        if csv_data is None:
            csv_data = self.view.csv_templates.currentData()

        if csv_data is None:
            return

        self.view.settings["csv_fields"].clear()

        for key, value in csv_data:
            self.view.settings["csv_fields"].add_item(key, value)

    def export_versions(self):
        """Runs the export function on the model."""
        self.view.final_error_label.hide()
        self.view.final_success_label.hide()

        # Lock checkboxes
        for version in self.view.shot_widget_references.values():
            version["shot_deliver_sequence"].setDisabled(True)
            version["shot_deliver_preview"].setDisabled(True)

        user_settings = self.settings.user_settings

        if user_settings is None:
            self.view.final_error_label.show()
            return

        # Close settings
        self.view.settings_widget.setCollapsed(True)

        if not self.model.validate_all_shots(
            self.show_validation_error, self.show_validation_message
        ):
            return

        self.setup_progress(user_settings)

        self.model.export_versions(
            user_settings,
            self.show_validation_error,
            self.update_progress_bar,
            self.show_validation_message,
            self.finish_export_versions,
            self.get_deliverables,
        )

    def setup_progress(self, user_settings: UserSettings):
        """
        Setup global progress bar at start of export.
        """
        self.progress_values = {}
        self.progress_amounts = 0
        self.view.progress_bar.show()
        self.view.progress_bar.setValue(0)

        for shot in self.model.shots_to_deliver:
            for version in shot.get_versions():
                deliverables = self.get_deliverables(version)

                amount = int(deliverables.deliver_preview) * len(
                    user_settings.delivery_preview_outputs
                ) + int(deliverables.deliver_sequence)
                self.progress_amounts += amount
                self.progress_values[version.id_str] = {
                    "value": 0,
                    "amount": amount,
                }

    def finish_export_versions(self):
        """
        Callback for when exporting versions is done.
        """
        # Unlock checkboxes
        for key, version in self.view.shot_widget_references.items():
            version["shot_deliver_sequence"].setDisabled(False)
            version["shot_deliver_preview"].setDisabled(False)

        self.view.final_success_label.show()
        self.view.progress_bar.hide()

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
        self.view.final_error_label.show()

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
        """Updates the global progress bar and on a version.

        Args:
            version: Version to change progress bar on
        """
        self.view.shot_widget_references[version.id_str][
            "shot_progress_bar"
        ].setValue(version.progress * 100)
        self.progress_values[version.id_str]["value"] = version.progress

        global_progress = 0

        for value in self.progress_values.values():
            global_progress += (
                value["value"] * value["amount"] / self.progress_amounts
            )

        self.view.progress_bar.setValue(global_progress * 99)

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

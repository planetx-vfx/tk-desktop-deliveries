from __future__ import annotations

import contextlib
import csv
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from sgtk.platform.qt5 import QtCore, QtWidgets

from .models import Letterbox, Settings
from .models.field_template_string import FieldTemplateString

if TYPE_CHECKING:
    from .controller import DeliveryController
    from .model import DeliveryModel
    from .view import DeliveryView
    from .widgets import OrderedListItem

# For development only
with contextlib.suppress(ImportError):
    from PySide6 import QtCore, QtWidgets


class DeliveryActions:
    parent: DeliveryController
    view: DeliveryView
    model: DeliveryModel
    settings: Settings

    def __init__(
        self,
        parent,
        view: DeliveryView,
        model: DeliveryModel,
        settings: Settings,
    ):
        self.parent = parent
        self.view = view
        self.model = model
        self.settings = settings

        csv_template_folder_template = self.parent.app.get_template(
            "csv_template_folder"
        )
        self.csv_template_folder = Path(
            csv_template_folder_template.apply_fields({})
        )

        self.load_letterbox_defaults(self.model.get_project())

    def load_shots(self, success: Callable, error: Callable):
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
        self.model.load_shots_data(success, error)

    # --- Buttons ---
    def open_delivery_folder(self):
        """Opens the delivery folder."""
        self.model.open_delivery_folder()

    # --- Delivery Version ---
    def on_delivery_version_change(self):
        delivery_version = None
        if self.view.settings["override_delivery_version"].isChecked():
            delivery_version = int(
                self.view.settings["delivery_version"].text()
            )

        self.settings.user_settings.delivery_version = delivery_version

    # --- Delivery Location ---
    def on_delivery_location_change(self):
        self.view.settings["delivery_location"].setProperty("cssClass", "")
        self.view.settings["delivery_location"].style().unpolish(
            self.view.settings["delivery_location"]
        )
        self.view.settings["delivery_location"].style().polish(
            self.view.settings["delivery_location"]
        )

        delivery_location = None
        text = self.view.settings["delivery_location"].text()

        if (
            self.view.settings["override_delivery_location"].isChecked()
            and text != ""
        ):
            filepath = Path(text)
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

        self.settings.user_settings.delivery_location = delivery_location

    # --- Letterbox ---
    def load_letterbox_defaults(self, project):
        """Load the default letterbox settings from the ShotGrid project"""
        self.view.settings["letterbox_enable"].setChecked(
            project["sg_output_preview_enable_mask"]
        )

        if project["sg_output_preview_aspect_ratio"] is not None:
            self.view.settings["letterbox_w"].setText(
                project["sg_output_preview_aspect_ratio"]
            )
            self.view.settings["letterbox_h"].setText("1")

    def on_letterbox_enable_change(self):
        letterbox = None
        if self._letterbox_is_valid():
            letterbox = Letterbox(
                float(self.view.settings["letterbox_w"].text()),
                float(self.view.settings["letterbox_h"].text()),
                float(self.view.settings["letterbox_opacity"].text()),
            )

        self.settings.user_settings.letterbox = letterbox

    def _letterbox_is_valid(self):
        return (
            self.view.settings["letterbox_enable"].isChecked()
            and self.view.settings["letterbox_w"].text() != ""
            and self.view.settings["letterbox_h"].text() != ""
            and self.view.settings["letterbox_opacity"].text() != ""
        )

    # --- Previews ---
    def on_previews_change(self):
        delivery_preview_outputs = []
        input_preview_outputs = list(
            enumerate(self.settings.delivery_preview_outputs)
        )
        input_preview_outputs.reverse()
        for i, output in input_preview_outputs:
            if self.view.settings[
                f"preview_output_{i}_enabled"
            ].isChecked() and not any(
                output.extension == out.extension
                for out in delivery_preview_outputs
            ):
                if self._letterbox_is_valid():
                    output.use_letterbox = self.view.settings[
                        f"preview_output_{i}_letterbox"
                    ].isChecked()
                delivery_preview_outputs.append(output)

        self.settings.user_settings.delivery_preview_outputs = (
            delivery_preview_outputs
        )

    # --- CSV ---
    def on_csv_change(self):
        csv_fields = []
        if self.view.settings["csv_fields"].size() > 0:
            for item in self.view.settings["csv_fields"].items:
                key, value = item.get_content()
                item: OrderedListItem

                item.reset_validation()
                try:
                    template = FieldTemplateString(value, self.parent.cache)
                    csv_fields.append((key, template))
                except:
                    item.fail_validation()
                    self.parent.logger.error(
                        "CSV field for %s is not a valid template: %s",
                        key,
                        value,
                    )
                    template = FieldTemplateString("-", self.parent.cache)
                    csv_fields.append((key, template))

        self.settings.user_settings.csv_fields = csv_fields

    def add_csv_entry(self):
        """Add an entry to the CSV list."""
        self.view.settings["csv_fields"].add_item("", "")

    def load_csv_templates(self):
        """Load CSV Template files"""
        csv_template_folder_template = self.parent.app.get_template(
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

    def load_csv_template_file(self, file_path: str) -> list[tuple[str, str]]:
        """
        Load the data from a csv template file.

        Args:
            file_path: CSV file path
        """
        self.parent.logger.debug(f"Loading CSV template: {file_path}")

        with Path(file_path).open(newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)
            data = list(zip(rows[0], rows[1]))

            file_name = Path(file_path).stem

            self.view.csv_templates.addItem(file_name, userData=data)

            return data

    def save_csv_template(self):
        """Save current CSV template."""
        text, ok = QtWidgets.QInputDialog.getText(
            self.parent, "Save CSV Template", "Enter the template name:"
        )
        if not ok:
            return

        if text == "":
            dialog = QtWidgets.QMessageBox(self.parent)
            dialog.setWindowTitle("Failed")
            dialog.setText("Failed saving template. Name is empty.")
            dialog.exec()
            return

        if not re.match(r"^[a-zA-Z0-9 _-]+$", text):
            dialog = QtWidgets.QMessageBox(self.parent)
            dialog.setWindowTitle("Failed")
            dialog.setText(
                "Failed saving template. Please only use [a-zA-Z0-9_- ]"
            )
            dialog.exec()
            return

        csv_template_path = self.csv_template_folder / f"{text}.csv"

        with Path(csv_template_path).open("w", newline="") as file:
            writer = csv.writer(file)
            header = [
                key for key, template in self.settings.user_settings.csv_fields
            ]
            keys = [
                template.template
                for key, template in self.settings.user_settings.csv_fields
            ]

            writer.writerow(header)
            writer.writerow(keys)

            dialog = QtWidgets.QMessageBox(self.parent)
            dialog.setWindowTitle("Success")
            dialog.setText("Saved template")
            dialog.exec()

            file.close()

            self.load_csv_templates()

    def load_csv_template(
        self, csv_data: dict[str, str] | list[tuple[str, str]] | None = None
    ):
        """Load the selected CSV template."""
        if csv_data is None:
            csv_data = self.view.csv_templates.currentData()

        if csv_data is None:
            return

        self.view.settings["csv_fields"].clear()

        for key, value in csv_data:
            self.view.settings["csv_fields"].add_item(key, value)

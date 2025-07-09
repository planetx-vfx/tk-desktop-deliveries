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
View for delivery tool, written by Mervin van Brakel 2024.
Updated by Max de Groot 2024.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from sgtk.platform.qt5 import QtCore, QtGui, QtSvg, QtWidgets

from .models.entity import EntityType
from .widgets import Collapse, OrderedList

if TYPE_CHECKING:
    from .models.asset import Asset
    from .models.shot import Shot
    from .models.version import Version

# # For development only
# try:
#     from PySide6 import QtCore, QtWidgets, QtSvg, QtGui
# except ImportError:
#     pass

SCRIPT_LOCATION: Path = Path(__file__).parent


class DeliveryView:
    """View for the ShotGrid delivery application.

    This view has all functions related to the Qt UI.
    """

    def __init__(self) -> None:
        self.shot_widget_references = {}
        self.settings = {}

    def create_user_interface(
        self, main_widget: QtWidgets.QWidget, default_csv_fields: dict
    ):
        """Creates the UI of the window.

        Args:
            main_widget: The main application widget. We get this from the controller because
            I couldn't get it to work properly otherwise..
            default_csv_fields: Dictionary of the default CSV fields and values
        """
        QtWidgets.QWidget.__init__(main_widget)

        self.layout = QtWidgets.QVBoxLayout(main_widget)
        self.layout.addWidget(self.get_settings_widget(default_csv_fields))
        self.layout.addWidget(self.get_shots_list_widget())
        self.layout.addWidget(self.get_footer_widget())

        main_widget.setStyleSheet(
            """
            QCheckBox, QLabel {
                font-size: 12px;
            }
            
            QLineEdit {
                border: 1px solid;
                border-color: #737373; /* neutral-500 */
                background-color: #525252; /* neutral-600 */
            }
            QLineEdit::disabled {
                border-color: #525252; /* neutral-600 */
                background-color: #404040; /* neutral-700 */
            }
            QLineEdit[cssClass~="validation-failed"] {
                border-color: #ef4444; /* RED-500 */
            }
            
            QCheckBox {
                padding: 0;
                margin: 0;
            }
            QCheckBox::indicator {
                border: 1px solid;
                width: 10px;
                height: 10px;
            }
            QCheckBox::indicator:unchecked {
                border-color: #737373; /* neutral-500 */
                background-color: #525252; /* neutral-600 */
            }
            QCheckBox::indicator:checked {
                border-color: #a3e635; /* lime-400 */
                background-color: #84cc16; /* lime-500 */
            }
            """
        )

    @staticmethod
    def get_explanation_widget() -> QtWidgets.QWidget:
        """Gets the explanation widget of the layout.

        Returns:
            Widget containing explanation.
        """
        explanation_widget = QtWidgets.QWidget()
        explanation_widget_layout = QtWidgets.QVBoxLayout()
        explanation_widget.setLayout(explanation_widget_layout)

        explanation_label_1 = QtWidgets.QLabel(
            "Welcome to the delivery application!"
        )
        explanation_widget_layout.addWidget(explanation_label_1)

        explanation_label_2 = QtWidgets.QLabel(
            "This application is used to create the final return files that we send back to our editors."
        )
        explanation_widget_layout.addWidget(explanation_label_2)

        explanation_label_3 = QtWidgets.QLabel(
            "Only shots with the status 'Ready for Delivery' show up in this program."
        )
        explanation_widget_layout.addWidget(explanation_label_3)

        explanation_label_4 = QtWidgets.QLabel(
            "This program only exports the latest version of the shots, so make sure shots are published correctly."
        )
        explanation_widget_layout.addWidget(explanation_label_4)

        return explanation_widget

    def get_settings_widget(
        self, default_csv_fields: dict
    ) -> QtWidgets.QWidget:
        """
        Gets the settings widget for the layout.

        Returns:
            Widget containing settings widgets.
        """
        self.settings_widget = Collapse(title="Settings")

        # --- Delivery version ---
        self.settings["delivery_version"] = QtWidgets.QLineEdit()
        self.settings["delivery_version"].setFixedWidth(40)
        self.settings["delivery_version"].setValidator(QtGui.QIntValidator())
        self.settings["delivery_version"].setText("1")
        self.settings["delivery_version"].setDisabled(True)

        self.settings["override_delivery_version"] = QtWidgets.QCheckBox(
            text="Override delivery version"
        )
        self.settings["override_delivery_version"].stateChanged.connect(
            lambda state: self.settings["delivery_version"].setDisabled(
                state != QtCore.Qt.Checked
            )
        )

        delivery_version = QtWidgets.QWidget()
        delivery_version_layout = QtWidgets.QHBoxLayout()
        delivery_version_layout.setContentsMargins(0, 0, 0, 0)

        delivery_version_layout.addWidget(
            self.settings["override_delivery_version"]
        )
        delivery_version_layout.addWidget(self.settings["delivery_version"])
        delivery_version_layout.addStretch()
        delivery_version.setLayout(delivery_version_layout)

        self.settings_widget.addWidget(delivery_version)

        # --- Delivery location ---
        self.settings["delivery_location"] = QtWidgets.QLineEdit()
        self.settings["delivery_location"].setDisabled(True)

        self.settings["override_delivery_location"] = QtWidgets.QCheckBox(
            text="Override delivery location"
        )
        self.settings["override_delivery_location"].stateChanged.connect(
            lambda state: self.settings["delivery_location"].setDisabled(
                state != QtCore.Qt.Checked
            )
        )

        delivery_location = QtWidgets.QWidget()
        delivery_location_layout = QtWidgets.QHBoxLayout()
        delivery_location_layout.setContentsMargins(0, 0, 0, 0)

        delivery_location_layout.addWidget(
            self.settings["override_delivery_location"]
        )
        delivery_location_layout.addWidget(self.settings["delivery_location"])
        delivery_location.setLayout(delivery_location_layout)

        self.settings_widget.addWidget(delivery_location)

        # --- Letterbox ---
        self.settings["letterbox_w"] = QtWidgets.QLineEdit()
        self.settings["letterbox_w"].setFixedWidth(40)
        self.settings["letterbox_w"].setValidator(QtGui.QDoubleValidator())
        self.settings["letterbox_w"].setText("16")
        self.settings["letterbox_w"].setDisabled(True)

        letterbox_ratio_label = QtWidgets.QLabel(":")

        self.settings["letterbox_h"] = QtWidgets.QLineEdit()
        self.settings["letterbox_h"].setFixedWidth(40)
        self.settings["letterbox_h"].setValidator(QtGui.QDoubleValidator())
        self.settings["letterbox_h"].setText("9")
        self.settings["letterbox_h"].setDisabled(True)

        letterbox_opacity_label = QtWidgets.QLabel("    Opacity")
        self.settings["letterbox_opacity"] = QtWidgets.QLineEdit()
        self.settings["letterbox_opacity"].setFixedWidth(40)
        self.settings["letterbox_opacity"].setValidator(
            QtGui.QDoubleValidator()
        )
        self.settings["letterbox_opacity"].setText("0.5")
        self.settings["letterbox_opacity"].setDisabled(True)

        self.settings["letterbox_enable"] = QtWidgets.QCheckBox(
            text="Letterbox"
        )

        def update_letterbox_state(state):
            for setting in ["letterbox_w", "letterbox_h", "letterbox_opacity"]:
                self.settings[setting].setDisabled(state != QtCore.Qt.Checked)

            if "preview_outputs" in self.settings:
                for output in self.settings["preview_outputs"]:
                    self.settings[f"{output}_letterbox"].setDisabled(
                        state != QtCore.Qt.Checked
                    )
                    self.settings[f"{output}_letterbox"].setChecked(
                        state == QtCore.Qt.Checked
                    )

        self.settings["letterbox_enable"].stateChanged.connect(
            update_letterbox_state
        )

        letterbox = QtWidgets.QWidget()
        letterbox_layout = QtWidgets.QHBoxLayout()
        letterbox_layout.setContentsMargins(0, 0, 0, 0)

        letterbox_layout.addWidget(self.settings["letterbox_enable"])
        letterbox_layout.addWidget(self.settings["letterbox_w"])
        letterbox_layout.addWidget(letterbox_ratio_label)
        letterbox_layout.addWidget(self.settings["letterbox_h"])
        letterbox_layout.addWidget(letterbox_opacity_label)
        letterbox_layout.addWidget(self.settings["letterbox_opacity"])
        letterbox_layout.addStretch()

        letterbox.setLayout(letterbox_layout)

        self.settings_widget.addWidget(letterbox)

        # --- PREVIEWS ---
        self.preview_outputs = Collapse(title="Previews")
        self.settings_widget.addWidget(self.preview_outputs)

        # --- CSV ---
        csv_settings = Collapse(title="CSV")

        csv_heading = QtWidgets.QWidget()
        csv_heading_layout = QtWidgets.QHBoxLayout()
        csv_heading_layout.setContentsMargins(0, 0, 0, 0)

        csv_label = QtWidgets.QLabel("CSV Fields (ℹ)")
        csv_label_tooltip = [
            "<b>Available fields:</b>",
            "- file.name",
            "- file.name_ranged",
            "- file.codec",
            "- file.folder",
            "- date.&lt;format&gt;",
            "- project.*",
            "- shot.*",
            "- version.*",
            "",
            "&lt;format&gt; is a date format using Python Date Format Codes.",
            "* are all ShotGrid fields for the corresponding entity.",
            "Use {} for an expression, or none for regular text.",
        ]
        csv_label.setToolTip("<br>".join(csv_label_tooltip))

        csv_heading_layout.addWidget(csv_label)
        csv_heading_layout.addStretch()

        self.csv_templates = QtWidgets.QComboBox()
        csv_heading_layout.addWidget(self.csv_templates)

        self.csv_save_button = QtWidgets.QPushButton("Save")
        self.csv_save_button.setFixedWidth(40)
        csv_heading_layout.addWidget(self.csv_save_button)

        self.csv_load_button = QtWidgets.QPushButton("Load")
        self.csv_load_button.setFixedWidth(40)
        csv_heading_layout.addWidget(self.csv_load_button)

        self.csv_add_button = QtWidgets.QPushButton("+")
        self.csv_add_button.setFixedWidth(24)
        csv_heading_layout.addWidget(self.csv_add_button)

        csv_heading.setLayout(csv_heading_layout)
        csv_settings.addWidget(csv_heading)

        self.settings["csv_fields"] = OrderedList()
        for key, value in default_csv_fields.items():
            self.settings["csv_fields"].add_item(key, str(value))

        csv_settings.addWidget(self.settings["csv_fields"])

        self.settings_widget.addWidget(csv_settings)

        return self.settings_widget

    def get_shots_list_widget(self) -> QtWidgets.QWidget:
        """Gets the shot list widget of the layout.

        Returns:
            Widget containing shot list.
        """
        self.shots_list_scroll_area = QtWidgets.QScrollArea()
        self.shots_list_widget = QtWidgets.QWidget()
        self.shots_list_widget_layout = QtWidgets.QVBoxLayout()
        self.shots_list_widget.setLayout(self.shots_list_widget_layout)

        self.shots_list_widget.setStyleSheet("background-color:#2A2A2A;")
        self.shots_list_widget_layout.addWidget(self.get_loading_widget())

        self.shots_list_scroll_area.setWidget(self.shots_list_widget)
        self.shots_list_scroll_area.setWidgetResizable(True)

        return self.shots_list_scroll_area

    def get_footer_widget(self) -> QtWidgets.QWidget:
        """Gets the buttons widget of the layout.

        Returns:
            Widget containing buttons.
        """
        footer_widget = QtWidgets.QWidget()
        footer_widget_layout = QtWidgets.QVBoxLayout()
        footer_widget.setLayout(footer_widget_layout)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.hide()
        footer_widget_layout.addWidget(self.progress_bar)

        self.final_error_label = QtWidgets.QLabel(
            "The delivery failed due to errors!"
        )
        self.final_error_label.hide()
        self.final_error_label.setStyleSheet(
            "color: '#FF3E3E'; font: bold; font-size: 12px"
        )
        footer_widget_layout.addWidget(self.final_error_label)

        self.final_success_label = QtWidgets.QLabel("Delivery finished.")
        self.final_success_label.hide()
        self.final_success_label.setStyleSheet(
            "color: '#8BFF3E'; font: bold; font-size: 12px"
        )
        footer_widget_layout.addWidget(self.final_success_label)

        self.reload_button = QtWidgets.QPushButton("Reload shot list")
        footer_widget_layout.addWidget(self.reload_button)

        self.export_shots_button = QtWidgets.QPushButton("Export shots")
        footer_widget_layout.addWidget(self.export_shots_button)

        self.open_delivery_folder_button = QtWidgets.QPushButton(
            "Open delivery folder"
        )
        footer_widget_layout.addWidget(self.open_delivery_folder_button)

        return footer_widget

    def get_loading_widget(self) -> QtWidgets.QWidget:
        """Gets the loading widget for the layout.

        Returns:
            Widget containing loading widgets.
        """
        self.loading_widget = QtWidgets.QWidget()
        loading_widget_layout = QtWidgets.QVBoxLayout()
        loading_widget_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_widget.setLayout(loading_widget_layout)

        loading_spinner = QtSvg.QSvgWidget(
            str(
                SCRIPT_LOCATION / "../.." / "resources" / "loading_spinner.svg"
            )
        )
        loading_spinner.setFixedSize(100, 100)
        loading_widget_layout.addWidget(
            loading_spinner, 0, QtCore.Qt.AlignHCenter
        )

        return self.loading_widget

    def get_version_widget(
        self, entity: Shot | Asset, version: Version
    ) -> QtWidgets.QWidget:
        """Gets the shot widget for the layout. It also stores this
        widget in the reference list so we can update its UI later.

        Args:
            entity: Shot or Asset information dictionary

        Returns:
            Widget for shot information.
        """
        self.shot_widget_references[version.id_str] = {}

        self.shot_widget_references[version.id_str][
            "widget"
        ] = QtWidgets.QWidget()
        shot_widget_main_layout = QtWidgets.QHBoxLayout()
        self.shot_widget_references[version.id_str]["widget"].setLayout(
            shot_widget_main_layout
        )

        shot_widget_vertical_layout = QtWidgets.QVBoxLayout()

        if version.thumbnail is not None and version.thumbnail != "":
            with urllib.request.urlopen(version.thumbnail) as response:
                image_data = response.read()

            # Load image into QPixmap
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(image_data)
            scaled_pixmap = pixmap.scaledToWidth(
                128, QtCore.Qt.SmoothTransformation
            )

            image_label = QtWidgets.QLabel()
            image_label.setPixmap(scaled_pixmap)
            shot_widget_main_layout.addWidget(image_label)
        else:
            shot_widget_main_layout.addSpacing(128)

        shot_name_label = QtWidgets.QLabel(
            f"{entity.code} - Version {version.version_number}"
        )
        if entity.type == EntityType.SHOT:
            shot_name_label.setText(
                f"Sequence {entity.sequence} - Shot {entity.code} - Version {version.version_number}"
            )
        elif entity.type == EntityType.ASSET:
            shot_name_label.setText(
                f"Asset {entity.code} - Version {version.version_number}"
            )

        shot_name_label.setStyleSheet("font: bold; font-size: 14px")
        shot_widget_vertical_layout.addWidget(shot_name_label)

        shot_widget_settings = QtWidgets.QWidget()
        shot_widget_settings_layout = QtWidgets.QHBoxLayout()
        shot_widget_settings_layout.setContentsMargins(0, 0, 0, 0)
        shot_widget_settings.setLayout(shot_widget_settings_layout)

        shot_info_label = QtWidgets.QLabel(
            f"Frames {version.first_frame} - {version.last_frame}"
        )
        shot_info_label.setStyleSheet("font-size: 12px")
        shot_widget_settings_layout.addWidget(shot_info_label)

        self.shot_widget_references[version.id_str][
            "shot_deliver_sequence"
        ] = QtWidgets.QCheckBox(text="Deliver EXRs")
        self.shot_widget_references[version.id_str][
            "shot_deliver_sequence"
        ].setChecked(
            version.deliver_sequence and version.sequence_path is not None
        )
        self.shot_widget_references[version.id_str][
            "shot_deliver_sequence"
        ].setDisabled(version.sequence_path is None)
        shot_widget_settings_layout.addWidget(
            self.shot_widget_references[version.id_str][
                "shot_deliver_sequence"
            ]
        )

        self.shot_widget_references[version.id_str]["shot_deliver_preview"] = (
            QtWidgets.QCheckBox(text="Deliver Preview")
        )
        self.shot_widget_references[version.id_str][
            "shot_deliver_preview"
        ].setChecked(
            version.deliver_preview and version.path_to_movie is not None
        )
        self.shot_widget_references[version.id_str][
            "shot_deliver_preview"
        ].setDisabled(version.path_to_movie is None)
        shot_widget_settings_layout.addWidget(
            self.shot_widget_references[version.id_str]["shot_deliver_preview"]
        )

        shot_widget_vertical_layout.addWidget(shot_widget_settings)

        self.shot_widget_references[version.id_str]["validation_label"] = (
            QtWidgets.QLabel("Version ready for export!")
        )
        self.shot_widget_references[version.id_str][
            "validation_label"
        ].setStyleSheet("color: '#8BFF3E'; font-size: 10px;")
        shot_widget_vertical_layout.addWidget(
            self.shot_widget_references[version.id_str]["validation_label"]
        )

        self.shot_widget_references[version.id_str][
            "shot_progress_bar"
        ] = QtWidgets.QProgressBar()
        self.shot_widget_references[version.id_str][
            "shot_progress_bar"
        ].setMinimum(0)
        self.shot_widget_references[version.id_str][
            "shot_progress_bar"
        ].setMaximum(100)
        self.shot_widget_references[version.id_str][
            "shot_progress_bar"
        ].setStyleSheet(
            "QProgressBar::chunk {background-color: #8BFF3E;} QProgressBar {color: black; background-color: #444444; text-align: center;}"
        )
        shot_widget_vertical_layout.addWidget(
            self.shot_widget_references[version.id_str]["shot_progress_bar"]
        )

        shot_details = QtWidgets.QWidget()
        shot_details.setLayout(shot_widget_vertical_layout)
        shot_widget_main_layout.addWidget(shot_details)

        return self.shot_widget_references[version.id_str]["widget"]

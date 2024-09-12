from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from sgtk.platform.qt5 import QtCore

from . import Version, Deliverables, UserSettings


# # For development only
# try:
#     from PySide6 import QtCore
# except ImportError:
#     pass


class ExportShotsThread(QtCore.QThread):
    """Class for exporting shots on a separate thread
    so the UI doesn't freeze."""

    def __init__(
        self,
        model: DeliveryModel,
        show_validation_error: Callable[[Version], None],
        update_progress_bars: Callable[[Version], None],
        show_validation_message: Callable[[Version], None],
        get_deliverables: Callable[[Version], Deliverables],
    ):
        super().__init__()
        self.model = model
        self.show_validation_error = show_validation_error
        self.update_progress_bars = update_progress_bars
        self.show_validation_message = show_validation_message
        self.get_deliverables = get_deliverables

    def run(self):
        validated_shots = self.model.validate_all_shots(
            self.show_validation_error, self.show_validation_message
        )

        episodes = set([shot.episode for shot in validated_shots])
        episode_delivery_versions = {}

        delivery_folder_template = self.model.app.get_template(
            "delivery_folder"
        )
        delivery_sequence_template = self.model.app.get_template(
            "delivery_sequence"
        )
        delivery_preview_template = self.model.app.get_template(
            "delivery_preview"
        )

        for episode in episodes:
            # Get latest delivery version
            template_fields = {
                **self.model.base_template_fields,
                "Episode": episode,
            }

            unsafe_folder_version = True
            while unsafe_folder_version:
                delivery_folder = delivery_folder_template.apply_fields(
                    template_fields
                )
                if Path(delivery_folder).is_dir():
                    template_fields["delivery_version"] += 1
                else:
                    unsafe_folder_version = False

            # TODO check only enabled episodes
            # Create delivery folder
            delivery_folder = Path(
                delivery_folder_template.apply_fields(template_fields)
            )
            self.model.logger.info(
                f"Creating folder for delivery {delivery_folder}."
            )
            delivery_folder.mkdir(parents=True, exist_ok=True)

            # Store delivery version
            episode_delivery_versions[episode] = template_fields[
                "delivery_version"
            ]

            # Create csv
            csv_submission_form_template = self.model.app.get_template(
                "csv_submission_form"
            )
            csv_submission_form_path = (
                csv_submission_form_template.apply_fields(template_fields)
            )

            with open(csv_submission_form_path, "w", newline="") as file:
                writer = csv.writer(file)
                header = [
                    "Version Name",
                    "Link",
                    "VFX Scope of Work",
                    "Vendor",
                    "Submitting For",
                    "Submission Note",
                ]

                writer.writerow(header)

                for shot in validated_shots:
                    if shot.episode != episode:
                        continue

                    for version in shot.get_versions():
                        version_template_fields = (
                            self.model.get_version_template_fields(
                                shot,
                                version,
                                template_fields["delivery_version"],
                            )
                        )

                        deliverables = self.get_deliverables(version)

                        to_deliver = []
                        if deliverables.deliver_sequence:
                            sequence_name = Path(
                                delivery_sequence_template.apply_fields(
                                    version_template_fields
                                )
                            ).name
                            to_deliver.append(sequence_name)
                        if deliverables.deliver_preview:
                            preview_name = Path(
                                delivery_preview_template.apply_fields(
                                    version_template_fields
                                )
                            ).name
                            to_deliver.append(preview_name)

                        for file_name in to_deliver:
                            writer.writerow(
                                [
                                    file_name,
                                    shot.code,
                                    shot.description,
                                    template_fields["vnd"],
                                    version.submitting_for,
                                    version.delivery_note,
                                ]
                            )

        for shot in validated_shots:
            for version in shot.get_versions():
                deliverables = self.get_deliverables(version)
                self.model.deliver_version(
                    shot,
                    version,
                    episode_delivery_versions[shot.episode],
                    deliverables,
                    self.show_validation_error,
                    self.show_validation_message,
                    self.update_progress_bars,
                )
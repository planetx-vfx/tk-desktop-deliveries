from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from sgtk.platform.qt5 import QtCore

from . import Version, Deliverables, UserSettings
from ..external import parse_exr_metadata


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
        model,  # DeliveryModel
        user_settings: UserSettings,
        show_validation_error: Callable[[Version], None],
        update_progress_bars: Callable[[Version], None],
        show_validation_message: Callable[[Version], None],
        finish_export_versions: Callable[[], None],
        get_deliverables: Callable[[Version], Deliverables],
    ):
        super().__init__()
        self.model = model
        self.user_settings = user_settings
        self.show_validation_error = show_validation_error
        self.update_progress_bars = update_progress_bars
        self.show_validation_message = show_validation_message
        self.finish_export_versions = finish_export_versions
        self.get_deliverables = get_deliverables

    def run(self):
        version_deliverables = {}
        episodes = []
        for shot in self.model.shots_to_deliver:
            for version in shot.get_versions():
                deliverables = self.get_deliverables(version)

                if (
                    deliverables.deliver_preview
                    or deliverables.deliver_sequence
                ):
                    version_deliverables[version.id] = deliverables
                    if shot.episode not in episodes:
                        episodes.append(shot.episode)

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

        csv_episode_data = {}

        for episode in episodes:
            # Get latest delivery version
            template_fields = {
                **self.model.base_template_fields,
                "Episode": episode,
            }

            if self.user_settings.delivery_version is None:
                unsafe_folder_version = True
                while unsafe_folder_version:
                    tmp_delivery_folder = Path(
                        delivery_folder_template.apply_fields(template_fields)
                    )

                    # Override delivery location from user settings
                    if self.user_settings.delivery_location is not None:
                        base_path = Path(self.user_settings.delivery_location)
                        tmp_delivery_folder = (
                            base_path / tmp_delivery_folder.name
                        )

                    if tmp_delivery_folder.is_dir():
                        template_fields["delivery_version"] += 1
                    else:
                        unsafe_folder_version = False
            else:
                template_fields["delivery_version"] = (
                    self.user_settings.delivery_version
                )

            # Create delivery folder
            delivery_folder = Path(
                delivery_folder_template.apply_fields(template_fields)
            )

            # Override delivery location from user settings
            if self.user_settings.delivery_location is not None:
                base_path = Path(self.user_settings.delivery_location)
                delivery_folder = base_path / delivery_folder.name

            self.model.logger.info(
                f"Creating folder for delivery {delivery_folder}."
            )
            delivery_folder.mkdir(parents=True, exist_ok=True)

            # Store delivery version
            episode_delivery_versions[episode] = template_fields[
                "delivery_version"
            ]

            csv_episode_data[episode] = {
                "delivery_folder": delivery_folder,
                "template_fields": template_fields,
            }

        for shot in self.model.shots_to_deliver:
            for version in shot.get_versions():
                if version.id in version_deliverables:
                    self.model.deliver_version(
                        shot,
                        version,
                        episode_delivery_versions[shot.episode],
                        version_deliverables[version.id],
                        self.user_settings,
                        self.show_validation_error,
                        self.show_validation_message,
                        self.update_progress_bars,
                    )

        for episode in episodes:
            # Create csv
            self.create_csv(
                self.model.shots_to_deliver,
                episode,
                csv_episode_data[episode]["delivery_folder"],
                csv_episode_data[episode]["template_fields"],
                delivery_sequence_template,
                delivery_preview_template,
            )

        self.finish_export_versions()

    def format_field(self, field: any) -> str:
        if field is None:
            return ""

        if isinstance(field, str):
            return re.sub(r"[^\x20-\x7E\n\r\t]+", "", field)

        try:
            return str(field)
        except:
            return ""

    def create_csv(
        self,
        validated_shots: list,
        episode: str | None,
        delivery_folder: Path,
        template_fields: dict,
        delivery_sequence_template,
        delivery_preview_template,
    ):
        """
        Create the CSV file.
        """
        csv_submission_form_template = self.model.app.get_template(
            "csv_submission_form"
        )
        csv_submission_form_path: Path = Path(
            csv_submission_form_template.apply_fields(template_fields)
        )
        if self.user_settings.delivery_location is not None:
            csv_submission_form_path = (
                delivery_folder / csv_submission_form_path.name
            )

        existing_rows = []
        if csv_submission_form_path.is_file():
            with open(csv_submission_form_path, "r", newline="") as file:
                reader = csv.reader(file)
                header = []
                for i, row in enumerate(reader):
                    if i == 0:
                        header = row
                    else:
                        entry = {}
                        for j in range(0, len(header)):
                            entry[header[j]] = row[j]

                        existing_rows.append(entry)

        with open(csv_submission_form_path, "w", newline="") as file:
            writer = csv.writer(file)
            header = [key for key, value in self.user_settings.csv_fields]

            writer.writerow(header)

            for existing_row in existing_rows:
                row = []
                for item in header:
                    if item in existing_row:
                        row.append(existing_row[item])
                    else:
                        row.append("")
                writer.writerow(row)

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
                        sequence_path = Path(
                            delivery_sequence_template.apply_fields(
                                version_template_fields
                            )
                        )
                        to_deliver.append((sequence_path, ""))
                    if deliverables.deliver_preview:
                        for (
                            output
                        ) in self.user_settings.delivery_preview_outputs:
                            output_template_fields = {
                                **version_template_fields,
                                "delivery_preview_extension": output.extension,
                            }
                            preview_path = Path(
                                delivery_preview_template.apply_fields(
                                    output_template_fields
                                )
                            )
                            to_deliver.append(
                                (
                                    preview_path,
                                    output.name,
                                )
                            )

                    csv_data = {}
                    for (
                        entity,
                        fields,
                    ) in self.user_settings.get_csv_entities():
                        if entity in ["file", "date"]:
                            continue

                        entity_id = None
                        if entity == "project":
                            entity_id = self.model.context.project["id"]
                        elif entity == "shot":
                            entity_id = shot.id
                        elif entity == "version":
                            entity_id = version.id

                        sg_entity = self.model.shotgrid_connection.find_one(
                            entity[0].upper() + entity[1:],
                            [["id", "is", entity_id]],
                            fields,
                        )
                        if sg_entity is not None:
                            csv_data[entity] = sg_entity
                        else:
                            csv_data[entity] = {}

                    for file_path, codec in to_deliver:
                        file_name = file_path.name
                        output_file_path = file_path.as_posix()

                        csv_fields = []

                        if not file_path.exists():
                            error_msg = f'The file(s) of the delivered version "{version.code}" could not be found! Skipping row in CSV. {file_path.as_posix()}'
                            try:
                                first_frame_path = file_path.with_name(
                                    file_name % version.last_frame
                                )
                                if not first_frame_path.exists():
                                    self.model.logger.error(error_msg)
                                    continue
                            except:
                                self.model.logger.error(error_msg)
                                continue

                        for key, value in self.user_settings.csv_fields:
                            if isinstance(value, str):
                                csv_fields.append(value)
                                continue

                            entity, field = value

                            if entity == "file":
                                if field == "name":
                                    csv_fields.append(file_name)
                                    continue

                                elif (
                                    field == "codec" or field == "compression"
                                ):
                                    if codec != "":
                                        csv_fields.append(codec)
                                        continue

                                    if file_name.endswith(".exr"):
                                        try:
                                            metadata = parse_exr_metadata.read_exr_header(
                                                output_file_path
                                                % version.last_frame
                                            )
                                            if "compression" in metadata:
                                                csv_fields.append(
                                                    metadata.get(
                                                        "compression", ""
                                                    ).replace(
                                                        "_COMPRESSION", ""
                                                    )
                                                )
                                            else:
                                                csv_fields.append("")
                                        except:
                                            csv_fields.append("")
                                        continue
                                    else:
                                        csv_fields.append("")
                                    continue
                                elif field == "folder":
                                    csv_fields.append(delivery_folder.name)
                                    continue

                            if entity == "version" and field == "attachment":
                                if (
                                    version.attachment is not None
                                    and version.attachment["link_type"]
                                    in ["upload", "local"]
                                ):
                                    csv_fields.append(
                                        version.attachment["name"]
                                    )
                                    continue
                                else:
                                    csv_fields.append("")
                                    continue

                            if entity == "date":
                                date = datetime.now()

                                # Try to format the date
                                try:
                                    date_string = date.strftime(field)
                                except:
                                    date_string = str(date)
                                    msg = f'Failed to convert date to format "{field}".'
                                    self.model.logger.error(msg)

                                csv_fields.append(date_string)
                                continue

                            if entity in csv_data and (
                                field in csv_data[entity]
                                and csv_data[entity][field] is not None
                            ):
                                csv_fields.append(csv_data[entity][field])
                                continue

                            # Add empty string if no value found
                            csv_fields.append("")

                        # Sanitize text
                        csv_fields = [
                            self.format_field(field) for field in csv_fields
                        ]

                        self.model.logger.debug("Writing row:")
                        self.model.logger.debug(list(zip(header, csv_fields)))

                        writer.writerow(csv_fields)

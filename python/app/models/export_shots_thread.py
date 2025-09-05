from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from sgtk.platform.qt5 import QtCore

from .entity import EntityType
from .util import compile_extra_template_fields, EXR_COMPRESSION

if TYPE_CHECKING:
    from . import Deliverables, UserSettings, Version
    from .asset import Asset
    from .shot import Shot

from .context import Context, FileContext
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
        episodes = [None]
        for entity in (
            self.model.shots_to_deliver + self.model.assets_to_deliver
        ):
            for version in entity.get_versions():
                deliverables = self.get_deliverables(version)

                if (
                    deliverables.deliver_preview
                    or deliverables.deliver_sequence
                ):
                    version_deliverables[version.id] = deliverables
                    if (
                        entity.type == EntityType.SHOT
                        and entity.episode not in episodes
                    ):
                        episodes.append(entity.episode)

        episode_delivery_versions = {}

        delivery_folder_template = self.model.app.get_template(
            "delivery_folder"
        )

        csv_episode_data = {}

        for episode in episodes:
            # Get latest delivery version
            template_fields = {
                **self.model.base_template_fields,
                "Episode": episode,
            }

            if self.user_settings.delivery_version is None:
                fields = []

                base_template_path = Path(
                    delivery_folder_template.apply_fields(template_fields)
                ).parent
                base_path = base_template_path

                # Override delivery location from user settings
                if self.user_settings.delivery_location is not None:
                    base_path = Path(self.user_settings.delivery_location)

                for item in base_path.iterdir():
                    if item.is_file():
                        continue

                    # If iterating over non-templated folders, fake the base folder for getting the fields
                    if self.user_settings.delivery_location is not None:
                        item = base_template_path / item.name

                    try:
                        fields.append(
                            delivery_folder_template.get_fields(str(item))
                        )
                    except:
                        continue

                # Compile the version numbers. Filter on date if not using continuous versioning.
                delivered_versions = [
                    field["delivery_version"]
                    for field in fields
                    if self.model.settings.continuous_versioning
                    or field["delivery_date"].date() == datetime.now().date()
                ]

                template_fields["delivery_version"] = (
                    max(delivered_versions or [0]) + 1
                )
            else:
                template_fields["delivery_version"] = (
                    self.user_settings.delivery_version
                )

            # Store delivery version
            episode_delivery_versions[episode] = template_fields[
                "delivery_version"
            ]

            csv_episode_data[episode] = {
                "template_fields": template_fields,
            }

        episode_folders = "Episode" in delivery_folder_template.keys

        for episode in episodes if episode_folders else [None]:
            template_fields = csv_episode_data[episode]["template_fields"]

            # Create delivery folder
            delivery_folder = Path(
                delivery_folder_template.apply_fields(template_fields)
            )

            # Override delivery location from user settings
            if self.user_settings.delivery_location is not None:
                base_path = Path(self.user_settings.delivery_location)
                delivery_folder = base_path / delivery_folder.name

            self.model.logger.info(
                "Creating folder for delivery %s.", delivery_folder
            )
            delivery_folder.mkdir(parents=True, exist_ok=True)

            # If delivering for episodes, use the created folder
            if episode_folders:
                csv_episode_data[episode]["delivery_folder"] = delivery_folder
            else:
                # Make sure every episode has a delivery folder
                for ep in episodes:
                    csv_episode_data[ep]["delivery_folder"] = delivery_folder

        for entity in (
            self.model.shots_to_deliver + self.model.assets_to_deliver
        ):
            for version in entity.get_versions():
                if version.id in version_deliverables:
                    delivery_version = episode_delivery_versions.get(None)
                    if entity.type == EntityType.SHOT:
                        delivery_version = episode_delivery_versions[
                            entity.episode
                        ]

                    self.model.deliver_version(
                        entity,
                        version,
                        delivery_version,
                        version_deliverables[version.id],
                        self.user_settings,
                        self.show_validation_error,
                        self.show_validation_message,
                        self.update_progress_bars,
                    )

        for episode in episodes if episode_folders else [None]:
            # Create csv
            self.create_csv(
                (self.model.shots_to_deliver + self.model.assets_to_deliver),
                episode,
                csv_episode_data[episode]["delivery_folder"],
                csv_episode_data[episode]["template_fields"],
                episode_delivery_versions,
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
        validated_entities: list[Shot | Asset],
        episode: str | None,
        delivery_folder: Path,
        template_fields: dict,
        episode_delivery_versions: dict[str, int],
    ):
        """
        Create the CSV file.
        """
        self.model.logger.info("======== Creating CSV File ========")
        csv_submission_form_template = self.model.app.get_template(
            "csv_submission_form"
        )
        csv_submission_form_path: Path = Path(
            csv_submission_form_template.apply_fields(template_fields)
        )

        delivery_folder_org = Path(
            self.model.app.get_template("delivery_folder").apply_fields(
                template_fields
            )
        )

        if self.user_settings.delivery_location is not None:
            csv_submission_form_path = Path(
                csv_submission_form_path.as_posix().replace(
                    delivery_folder_org.as_posix(), delivery_folder.as_posix()
                )
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
            header = [key for key, template in self.user_settings.csv_fields]

            self.model.logger.debug("Header: %s", header)
            writer.writerow(header)

            for existing_row in existing_rows:
                row = []
                for item in header:
                    if item in existing_row:
                        row.append(existing_row[item])
                    else:
                        row.append("")
                writer.writerow(row)

            for entity in validated_entities:
                if (
                    entity.type == EntityType.SHOT
                    and entity.episode != episode
                    and "Episode"
                    in self.model.app.get_template("delivery_folder").keys
                ):
                    continue

                delivery_version = episode_delivery_versions.get(None)

                if entity.type == EntityType.SHOT:
                    delivery_sequence_template = self.model.app.get_template(
                        "delivery_shot_sequence"
                    )
                    delivery_preview_template = self.model.app.get_template(
                        "delivery_shot_preview"
                    )
                    delivery_version = episode_delivery_versions[
                        entity.episode
                    ]
                else:
                    delivery_sequence_template = self.model.app.get_template(
                        "delivery_asset_sequence"
                    )
                    delivery_preview_template = self.model.app.get_template(
                        "delivery_asset_preview"
                    )

                for version in entity.get_versions():
                    version_template_fields = (
                        self.model.get_version_template_fields(
                            entity,
                            version,
                            delivery_version,
                        )
                    )

                    version_template_fields = compile_extra_template_fields(
                        delivery_sequence_template,
                        self.model.cache,
                        entity,
                        version,
                        version_template_fields,
                    )

                    deliverables = self.get_deliverables(version)

                    to_deliver = []
                    if deliverables.deliver_sequence:
                        sequence_path = Path(
                            Path(
                                delivery_sequence_template.apply_fields(
                                    version_template_fields
                                )
                            )
                            .as_posix()
                            .replace(
                                delivery_folder_org.as_posix(),
                                delivery_folder.as_posix(),
                            )
                        )

                        seq_codec = ""
                        seq_bit_depth = ""
                        output = next(
                            (
                                o
                                for o in self.model.settings.delivery_sequence_outputs
                                if o.status == version.sequence_output_status
                            ),
                            None,
                        )
                        if output is not None:
                            seq_codec = output.settings.get("compression", "")
                            seq_bit_depth = (
                                output.settings.get("datatype") or ""
                            )

                        if (
                            seq_codec == "" or seq_bit_depth == ""
                        ) and version.sequence_path is not None:
                            try:
                                metadata = parse_exr_metadata.read_exr_header(
                                    version.sequence_path % version.last_frame
                                )
                                if (
                                    seq_codec == ""
                                    and "compression" in metadata
                                ):
                                    seq_codec = EXR_COMPRESSION.get(
                                        metadata.get("compression", ""),
                                        "unknown",
                                    )
                                if seq_bit_depth == "":
                                    channels = metadata.get("channels", {})
                                    if len(channels) > 0:
                                        pixel_type = next(
                                            iter(channels.values())
                                        )["pixel_type"]
                                        bit_depths = {
                                            0: "32-bit uint",
                                            1: "16-bit half",
                                            2: "32-bit float",
                                        }
                                        seq_bit_depth = bit_depths.get(
                                            pixel_type, ""
                                        )
                            except Exception:
                                pass

                        to_deliver.append(
                            (
                                sequence_path,
                                seq_codec,
                                seq_bit_depth,
                                self.model.settings.add_slate_to_sequence,
                            )
                        )
                    if deliverables.deliver_preview:
                        for (
                            output
                        ) in self.user_settings.delivery_preview_outputs:
                            output_template_fields = {
                                **version_template_fields,
                                "delivery_preview_extension": output.extension,
                            }
                            preview_path = Path(
                                Path(
                                    delivery_preview_template.apply_fields(
                                        output_template_fields
                                    )
                                )
                                .as_posix()
                                .replace(
                                    delivery_folder_org.as_posix(),
                                    delivery_folder.as_posix(),
                                )
                            )

                            bit_depth = ""
                            for value in output.settings.values():
                                if isinstance(value, str):
                                    match = re.search(
                                        r"(\d+)[ ]*-?bit",
                                        value,
                                        re.IGNORECASE,
                                    )
                                    if match:
                                        bit_depth = match.group(1) + "-bit"
                                        break

                            to_deliver.append(
                                (
                                    preview_path,
                                    output.name,
                                    bit_depth,
                                    True,
                                )
                            )

                    if (
                        entity.type == EntityType.SHOT
                        and (
                            deliverables.deliver_sequence
                            or deliverables.deliver_preview
                        )
                        and self.model.app.get_template("input_shot_lut")
                        is not None
                        and self.model.app.get_template("delivery_shot_lut")
                        is not None
                    ):
                        delivery_lut = Path(
                            Path(
                                self.model.app.get_template(
                                    "delivery_shot_lut"
                                ).apply_fields(version_template_fields)
                            )
                            .as_posix()
                            .replace(
                                delivery_folder_org.as_posix(),
                                delivery_folder.as_posix(),
                            )
                        )

                        to_deliver.append(
                            (
                                delivery_lut,
                                "",
                                "",
                                False,
                            )
                        )

                    for file_path, codec, bit_depth, has_slate in to_deliver:
                        file_name = file_path.name

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

                        for _key, template in self.user_settings.csv_fields:
                            context = Context(
                                shot=entity,
                                version=version,
                                file=FileContext(
                                    file_path=file_path,
                                    directory_path=delivery_folder,
                                    codec=codec,
                                    bit_depth=bit_depth,
                                    has_slate=has_slate,
                                ),
                                cache=self.model.cache,
                            )
                            try:
                                self.model.logger.debug(
                                    "Shot %s, Version %s, File %s",
                                    entity.id,
                                    version.id,
                                    file_path.name,
                                )
                                csv_fields.append(
                                    template.apply_context(context)
                                )
                            except Exception as err:
                                self.model.logger.error(err)
                                csv_fields.append("")

                        # Sanitize text
                        csv_fields = [
                            self.format_field(field) for field in csv_fields
                        ]

                        self.model.logger.debug("Writing row:")
                        self.model.logger.debug(list(zip(header, csv_fields)))

                        writer.writerow(csv_fields)
        self.model.logger.info("=" * 35)

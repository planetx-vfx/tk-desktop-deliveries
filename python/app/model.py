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
Model for delivery tool, written by Mervin van Brakel 2024.
Updated by Max de Groot 2024.
"""

from __future__ import annotations

import json
import os
import shutil
import traceback
from pathlib import Path
from typing import Callable
from urllib.request import urlretrieve

import sgtk

from .external import parse_exr_metadata
from .models import (
    Shot,
    Version,
    NukeProcess,
    Deliverables,
    Settings,
    UserSettings,
    ExportShotsThread,
    LoadShotsThread,
)
from .models.Errors import LicenseError
from .models.Version import Task


class ValidationError(Exception):
    """Gets raised when validation fails."""


class DeliveryModel:
    """Model for Delivery app"""

    settings: Settings
    shots_to_deliver: None | list[Shot]
    base_template_fields: dict
    load_shots_thread: None | LoadShotsThread
    export_shots_thread: None | ExportShotsThread

    def __init__(self, controller) -> None:
        """Initializes the model.

        Args:
            app: ShotGrid app
            logger: ShotGrid logger
        """
        app = controller.app
        self.app = app
        self.context = app.context
        self.shotgrid_connection = app.shotgun
        self.logger = app.logger
        self.shots_to_deliver = None
        self.load_shots_thread = None
        self.export_shots_thread = None

        self.settings = Settings(app)

        self.extra_fields = self.settings.compile_extra_fields()

        if sgtk.util.is_linux():
            self.nuke_path = "{}".format(app.get_setting("nuke_path_linux"))
            self.logo_path = "{}".format(app.get_setting("logo_path_linux"))
            self.font_path = "{}".format(app.get_setting("font_path_linux"))
            self.font_bold_path = "{}".format(
                app.get_setting("font_bold_path_linux")
            )
        elif sgtk.util.is_macos():
            self.nuke_path = "{}".format(app.get_setting("nuke_path_mac"))
            self.logo_path = "{}".format(app.get_setting("logo_path_mac"))
            self.font_path = "{}".format(app.get_setting("font_path_mac"))
            self.font_bold_path = "{}".format(
                app.get_setting("font_bold_path_mac")
            )
        elif sgtk.util.is_windows():
            self.nuke_path = "{}".format(app.get_setting("nuke_path_windows"))
            self.logo_path = "{}".format(app.get_setting("logo_path_windows"))
            self.font_path = "{}".format(app.get_setting("font_path_windows"))
            self.font_bold_path = "{}".format(
                app.get_setting("font_bold_path_windows")
            )

        # Set slate script path
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        self.slate_path = os.path.join(__location__, "slate_cli.py")
        self.plate_path = os.path.join(__location__, "plate_cli.py")

        self.sg_project = None
        self.base_template_fields = {
            "prj": self.get_project_code(),
            "delivery_version": 1,
            "vnd": self.get_vendor_id(),
        }

        controller.load_letterbox_defaults(self.get_project())

    def quit(self):
        """
        Cancel running threads before app quit
        """
        if self.load_shots_thread and self.load_shots_thread.isRunning():
            self.load_shots_thread.terminate()

        if self.export_shots_thread and self.export_shots_thread.isRunning():
            self.export_shots_thread.terminate()

    def open_delivery_folder(self) -> None:
        """Finds the correct path and opens the delivery folder."""
        template = self.app.get_template("delivery_folder")

        delivery_location = template.apply_fields(self.base_template_fields)
        delivery_folder = Path(delivery_location).parent

        os.startfile(delivery_folder)

    def load_shots(
        self,
        loading_shots_successful_function: Callable,
        loading_shots_failed_function: Callable,
    ) -> None:
        """Loads shots on a separate thread.

        Args:
            loading_shots_successful_function: Function that gets called when loading shots is successful.
            loading_shots_failed_function: Function that gets called when loading shots failed.
        """
        self.load_shots_thread = LoadShotsThread(self)

        self.load_shots_thread.loading_shots_successful.connect(
            loading_shots_successful_function
        )
        self.load_shots_thread.loading_shots_failed.connect(
            loading_shots_failed_function
        )

        self.load_shots_thread.start()

    def get_versions_to_deliver(self) -> list[Shot]:
        """Gets a list of shots with versions that are ready for delivery.

        Returns:
            List of shot information dictionaries.
        """
        self.logger.info("Starting 'ready for delivery' search.")
        project_id = self.context.project["id"]

        filters = [
            [
                "project",
                "is",
                {"type": "Project", "id": project_id},
            ],
            [
                self.settings.version_status_field,
                "is",
                self.settings.version_delivery_status,
            ],
        ]

        columns = list(
            {
                "code",
                "entity",
                "published_files",
                "sg_first_frame",
                "sg_last_frame",
                "sg_task",
                "sg_uploaded_movie_frame_rate",
                "sg_frames_have_slate",
                "sg_movie_has_slate",
                "sg_path_to_movie",
                "image",
                *self.extra_fields.get("Version", []),
            }
        )

        versions_to_deliver = self.shotgrid_connection.find(
            "Version", filters, columns
        )

        # Process entity overrides
        versions_to_deliver = self.process_entity_overrides(
            "Version", versions_to_deliver
        )

        shot_ids = {version["entity"]["id"] for version in versions_to_deliver}
        shots_to_deliver = []

        for shot_id in shot_ids:
            sg_shot = self.shotgrid_connection.find_one(
                "Shot",
                [["id", "is", shot_id]],
                [
                    "sg_sequence",
                    "code",
                    "description",
                    *self.extra_fields.get("Shot", []),
                ],
            )

            # Process entity overrides
            sg_shot = self.process_entity_overrides("Shot", sg_shot)

            sg_shot["versions"] = [
                version
                for version in versions_to_deliver
                if version["entity"]["id"] == shot_id
            ]
            shots_to_deliver.append(sg_shot)

        self.shots_to_deliver = self.get_shots_information_list(
            shots_to_deliver
        )

        self.shots_to_deliver = sorted(
            self.shots_to_deliver, key=lambda shot: (shot.sequence, shot.code)
        )

        self.logger.debug("Found shots to deliver:")
        for shot in self.shots_to_deliver:
            self.logger.debug(json.dumps(shot.as_dict(), indent=4))

        return self.shots_to_deliver

    def get_version_published_file(self, version: dict) -> dict | None:
        """Gets the correct published files associates with this version.

        Args:
            version: Version information

        Returns:
            Published files
        """
        publishes = version["published_files"]

        if len(publishes) == 0:
            return None

        filters = [
            ["id", "is", publishes[0]["id"]],
        ]

        columns = list(
            {
                "path",
                "published_file_type",
                "version_number",
                *self.extra_fields.get("PublishedFile", []),
            }
        )

        published_file = self.shotgrid_connection.find_one(
            "PublishedFile",
            filters,
            columns,
        )

        # Process entity overrides
        published_file = self.process_entity_overrides(
            "PublishedFile", published_file
        )

        return published_file

    def get_project(self) -> dict:
        """Gets the ShotGrid project.

        Returns:
            Project"""
        if self.sg_project is not None:
            return self.sg_project

        project_id = self.context.project["id"]
        filters = [
            [
                "id",
                "is",
                project_id,
            ]
        ]

        columns = list(
            {
                "name",
                "sg_short_name",
                "sg_vendorid",
                "sg_output_preview_aspect_ratio",
                "sg_output_preview_enable_mask",
                *self.extra_fields.get("Project", []),
            }
        )

        sg_project = self.shotgrid_connection.find_one(
            "Project", filters, columns
        )

        self.sg_project = self.process_entity_overrides("Project", sg_project)

        return self.sg_project

    def get_project_code(self) -> str:
        """Gets the ShotGrid project code.

        Returns:
            Project code"""
        return self.get_project()["sg_short_name"]

    def get_vendor_id(self) -> str:
        """Gets the vendor id.

        Returns:
            Vendor id"""
        return self.get_project()["sg_vendorid"]

    def get_episode_code(self, sequence: dict) -> int | None:
        """Gets the Episode code related to a Sequence.

        Returns:
            Episode code or None
        """
        filters = [
            ["project", "is", self.context.project],
            [
                "sequences",
                "is",
                sequence,
            ],
        ]

        columns = ["code"]
        episode = self.shotgrid_connection.find_one(
            "Episode", filters, columns
        )

        if episode is not None:
            return episode["code"]
        else:
            return None

    def get_shots_information_list(
        self, shots_to_deliver: list[dict]
    ) -> list[Shot]:
        """This function takes a list of shots and adds all the extra
        information we need for the rest of the program to function.

        Args:
            shots_to_deliver: List of shots to deliver

        Returns:
            List of shot information dicts
        """
        shots_information_list = []

        for sg_shot in shots_to_deliver:
            shot = Shot(
                sequence=sg_shot["sg_sequence"]["name"],
                code=sg_shot["code"],
                id=sg_shot["id"],
                description=sg_shot["description"],
                project_code=self.get_project_code(),
                episode=self.get_episode_code(sg_shot["sg_sequence"]),
            )

            for sg_version in sg_shot["versions"]:
                first_frame = sg_version["sg_first_frame"]
                last_frame = sg_version["sg_last_frame"]

                published_file = self.get_version_published_file(sg_version)
                sequence_path = ""
                if published_file is not None:
                    if sgtk.util.is_linux():
                        sequence_path = published_file["path"][
                            "local_path_linux"
                        ]
                    elif sgtk.util.is_macos():
                        sequence_path = published_file["path"][
                            "local_path_mac"
                        ]
                    elif sgtk.util.is_windows():
                        sequence_path = published_file["path"][
                            "local_path_windows"
                        ]

                task = None
                if sg_version["sg_task"] is not None:
                    task = Task(
                        sg_version["sg_task"]["id"],
                        sg_version["sg_task"]["name"],
                    )

                if (
                    sg_shot[self.settings.shot_status_field]
                    == self.settings.shot_delivery_status
                ):
                    deliver_preview = False
                    deliver_sequence = True
                else:
                    deliver_preview = True
                    deliver_sequence = False

                version = Version(
                    id=sg_version["id"],
                    code=sg_version["code"],
                    first_frame=first_frame,
                    last_frame=last_frame,
                    fps=sg_version["sg_uploaded_movie_frame_rate"],
                    thumbnail=sg_version["image"],
                    sequence_path=sequence_path,
                    version_number=(
                        published_file["version_number"]
                        if published_file is not None
                        else -1
                    ),
                    path_to_movie=sg_version["sg_path_to_movie"],
                    frames_have_slate=sg_version["sg_frames_have_slate"],
                    movie_has_slate=sg_version["sg_movie_has_slate"],
                    submitting_for=sg_version.get(
                        self.settings.submitting_for_field, ""
                    ),
                    submission_note=sg_version.get(
                        self.settings.submission_note_field, ""
                    ),
                    attachment=sg_version.get(
                        self.settings.attachment_field, ""
                    ),
                    task=task,
                    deliver_preview=deliver_preview,
                    deliver_sequence=deliver_sequence,
                    sequence_output_status=sg_version.get(
                        self.settings.delivery_sequence_outputs_field, ""
                    ),
                )
                shot.add_version(version)

            shots_information_list.append(shot)

        return shots_information_list

    def get_version_template_fields(
        self, shot: Shot, version: Version, delivery_version: int = None
    ) -> dict:
        """
        Get the template fields for a specific version
        Args:
            shot (Shot): Shot
            version (Version): Version
            delivery_version (int | None): Delivery version

        Returns:
            Template fields dict
        """
        template_fields = {
            **self.base_template_fields,
            "Sequence": shot.sequence,
            "Shot": shot.code,
            "version": version.version_number,
        }

        if delivery_version is not None:
            template_fields["delivery_version"] = delivery_version

        if version.task is not None:
            template_fields["task_name"] = version.task.name

        if shot.episode is not None:
            template_fields["Episode"] = shot.episode

        return template_fields

    def process_entity_overrides(
        self, entity_type: str, entities: dict | list
    ) -> dict | list:
        """
        Apply the version overrides from the configuration to ShotGrid loaded data

        Args:
            entity_type: The type of entity to look for
            entities: A dict or list of dicts
        """
        return_type = type(entities)
        if isinstance(entities, dict):
            entities = [entities]

        overrides = self.settings.get_version_overrides(entity_type)

        if len(overrides) == 0:
            if return_type is dict:
                return entities[0]
            else:
                return entities

        for entity in entities:
            self.logger.info(
                "Applying %s overrides to a %s.", len(overrides), entity_type
            )
            for override in overrides:
                entity = override.process(entity)

        if return_type is dict:
            return entities[0]
        else:
            return entities

    def validate_all_shots(
        self,
        show_validation_error: Callable[[Version], None],
        show_validation_message: Callable[[Version], None],
    ) -> bool:
        """Goes over all the shots and checks if all frames exist.

        Args:
            show_validation_error: Function for showing validation errors
            show_validation_message: Function for showing validation messages

        Returns:
            List of successfully validated shots

        Raises:
            ValidationError: Error when validation fails.
        """
        self.logger.info("Starting validation of shots.")

        success = True
        for shot in self.shots_to_deliver:
            self.logger.info(
                f"Validating sequence {shot.sequence}, shot {shot.code}."
            )
            for version in shot.get_versions():
                errors = []
                errors.extend(self.validate_fields(version))

                try:
                    if version.deliver_sequence:
                        # self.validate_sequence_filetype(version)
                        self.validate_all_frames_exist(version)
                except ValidationError as error_message:
                    errors.append(str(error_message))

                if len(errors) == 0:
                    self.logger.info("Validation passed.")

                    version.validation_message = (
                        "Initial validation checks passed!"
                    )
                    show_validation_message(version)
                else:
                    success = False
                    self.logger.error(
                        f'Version "{version.code}" ({version.id}) of shot {shot.sequence} {shot.code} had the following errors:'
                    )
                    for error in errors:
                        self.logger.error("- " + error)

                    error_message = "\n".join(errors)
                    version.validation_error = str(error_message)

                    # This is kinda sketchy, I know
                    show_validation_error(version)

        return success

    def validate_fields(self, version: Version) -> list[str]:
        """
        Validate ShotGrid fields required for delivery.

        Args:
            version: Version information

        Returns:
            Errors that occurred.
        """
        version_errors = []

        if version.first_frame is None or version.first_frame < 0:
            version_errors.append(
                "The sg_first_frame field on this version is empty or invalid."
            )
        if version.last_frame is None or version.last_frame < 0:
            version_errors.append(
                "The sg_last_frame field on this version is empty or invalid."
            )

        if version.fps is None or version.fps == "":
            version_errors.append(
                "The sg_uploaded_movie_frame_rate field on this version is empty."
            )

        if version.path_to_movie is None or version.path_to_movie == "":
            version_errors.append(
                "The path_to_movie field on this version is empty."
            )
        elif not os.path.isfile(version.path_to_movie):
            version_errors.append(
                "The path_to_movie field on this version points to a nonexistent file."
            )

        if version.sequence_path is None or version.sequence_path == "":
            version_errors.append("The published file(path) is empty.")
        else:
            if version.sequence_path.endswith(".mov"):
                version_errors.append(
                    "Linked version file on this version is a reference MOV, not an EXR sequence."
                )

            if version.version_number == -1:
                version_errors.append(
                    "The linked published file doesn't have a version."
                )

        return version_errors

    def validate_all_frames_exist(self, version: Version) -> list[str]:
        """Checks if all frames in the shot sequence exist

        Args:
            version: Version information

        Returns:
            Errors that occurred.
        """
        if (
            version.first_frame is None
            or version.first_frame < 0
            or version.last_frame is None
            or version.last_frame < 0
        ):
            return [
                "Shot version is missing frame range data (sg_first_frame, sg_last_frame)."
            ]

        errors = []
        for frame in range(version.first_frame, version.last_frame):
            try:
                frame_file_path = Path(version.sequence_path % frame)
            except TypeError:
                return [
                    "Could not format filepath. Are the EXRs correctly linked?"
                ]

            if not frame_file_path.is_file():
                errors.append(f"Can't find frame {frame}.")

        return errors

    def deliver_version(
        self,
        shot: Shot,
        version: Version,
        delivery_version: int,
        deliverables: Deliverables,
        user_settings: UserSettings,
        show_validation_error: Callable[[Version], None],
        show_validation_message: Callable[[Version], None],
        update_progress_bars: Callable[[Version], None],
    ) -> None:
        """Copies the shot to the right folder with the right naming conventions.

        Args:
            shot: Shot information
            version: Version information
            delivery_version: Version of the whole delivery
            deliverables: Deliverables object
            user_settings: User setting overrides
            show_validation_error: Function for showing validation errors
            show_validation_message: Function for showing validation message,
            update_progress_bars: Function for updating the progress bars
        """
        if deliverables.deliver_preview or deliverables.deliver_sequence:
            self.logger.debug(f"Delivering version {version.id}")
        else:
            self.logger.debug(f"Skipping delivery for version {version.id}")
            return

        try:
            input_sequence_template = self.app.get_template("input_sequence")
            delivery_folder_template = self.app.get_template("delivery_folder")
            preview_movie_template = self.app.get_template("preview_movie")
            delivery_sequence_template = self.app.get_template(
                "delivery_sequence"
            )
            delivery_preview_template = self.app.get_template(
                "delivery_preview"
            )

            template_fields = self.get_version_template_fields(
                shot, version, delivery_version
            )

            # Extract fields from preview path
            fields = preview_movie_template.validate_and_get_fields(
                version.path_to_movie
            )
            if fields is not None:
                template_fields = {**fields, **template_fields}

            # Get timecode ref path
            timecode_template_fields = {**template_fields, "version": 0}
            timecode_ref_path = None
            input_sequence = Path(
                input_sequence_template.apply_fields(timecode_template_fields)
            )
            input_frame = input_sequence.with_name(
                input_sequence.name % version.first_frame
            )
            if input_frame.is_file():
                timecode_ref_path = input_sequence
            else:
                input_sequence = Path(version.sequence_path)
                if Path(version.sequence_path % version.first_frame).is_file():
                    timecode_ref_path = input_sequence

            # Get the delivery folder
            delivery_folder = Path(
                delivery_folder_template.apply_fields(template_fields)
            )
            delivery_folder_org = delivery_folder

            # Get the input preview path
            preview_movie_file = Path(version.path_to_movie)

            # Get the output frame delivery path
            delivery_sequence_path = Path(
                delivery_sequence_template.apply_fields(template_fields)
            )

            # Override delivery location from user settings
            if user_settings.delivery_location is not None:
                delivery_folder_name = delivery_folder.name
                delivery_folder = (
                    Path(user_settings.delivery_location)
                    / delivery_folder_name
                )

                delivery_sequence_path = Path(
                    delivery_sequence_path.as_posix().replace(
                        str(delivery_folder_org), str(delivery_folder)
                    )
                )

            # Get count of total jobs
            preview_jobs = 0
            if deliverables.deliver_preview:
                preview_jobs = len(user_settings.delivery_preview_outputs)
            sequence_jobs = 0
            if deliverables.deliver_sequence:
                sequence_jobs = 1

            total_jobs = preview_jobs + sequence_jobs
            current_job = 0

            def update_progress(progress: float):
                version.progress = (progress + current_job) / total_jobs
                update_progress_bars(version)

            if deliverables.deliver_preview:
                for output in user_settings.delivery_preview_outputs:
                    preview_template_fields = {
                        **template_fields,
                        "delivery_preview_extension": output.extension,
                    }

                    # Get the output preview path
                    output_preview_path = Path(
                        delivery_preview_template.apply_fields(
                            preview_template_fields
                        )
                    )
                    if user_settings.delivery_location is not None:
                        output_preview_path = Path(
                            output_preview_path.as_posix().replace(
                                str(delivery_folder_org), str(delivery_folder)
                            )
                        )

                    self._deliver_preview(
                        shot,
                        version,
                        output,
                        user_settings,
                        preview_movie_file,
                        output_preview_path,
                        timecode_ref_path,
                        show_validation_error,
                        show_validation_message,
                        update_progress,
                    )

                    current_job += 1

            if deliverables.deliver_sequence:
                self._deliver_sequence(
                    shot,
                    version,
                    delivery_sequence_path,
                    show_validation_error,
                    show_validation_message,
                    update_progress,
                )

            # Deliver attachment
            self._deliver_attachment(version, user_settings, delivery_folder)

            # Update version data
            version_data = {}

            if not deliverables.deliver_sequence:
                version_data[self.settings.version_status_field] = (
                    self.settings.version_preview_delivered_status
                )
            else:
                version_data[self.settings.version_status_field] = (
                    self.settings.version_delivered_status
                )

            self.shotgrid_connection.update(
                "Version", version.id, version_data
            )

            # Update shot data
            if deliverables.deliver_sequence:
                shot_data = {
                    self.settings.shot_status_field: (
                        self.settings.shot_delivered_status
                    )
                }
                self.shotgrid_connection.update("Shot", shot.id, shot_data)

            version.validation_message = "Export finished!"
            show_validation_message(version)

        except FileExistsError:
            self.logger.error(
                "Files already exist. Has this shot been exported before?"
            )
            version.validation_error = (
                "Files already exist. Has this shot been exported before?"
            )
            show_validation_error(version)
        except LicenseError as error:
            self.logger.error(error)
            version.validation_error = "A Nuke license error occurred!"
            show_validation_error(version)
        except Exception:
            self.logger.error(traceback.format_exc())
            version.validation_error = "An error occurred while making the delivery, please check logs!"
            show_validation_error(version)

    def _deliver_preview(
        self,
        shot: Shot,
        version: Version,
        output,
        user_settings: UserSettings,
        preview_movie_file: Path,
        output_preview_path: Path,
        timecode_ref_path: Path | None,
        show_validation_error,
        show_validation_message,
        update_progress,
    ):

        slate_data = self._get_slate_data(version, shot)

        process = NukeProcess(
            version,
            show_validation_error,
            show_validation_message,
            update_progress,
            f"{output.extension.upper()} - {output.name}",
        )
        args = [
            "-t",
            self.slate_path,
            str(version.first_frame),
            str(version.last_frame),
            str(version.fps),
            preview_movie_file.as_posix(),
            output_preview_path.as_posix(),
            self.logo_path,
            "-idt",
            self.settings.preview_colorspace_idt,
            "-odt",
            self.settings.preview_colorspace_odt,
            "--font-path",
            self.font_path,
            "--font-bold-path",
            self.font_bold_path,
            "--write-settings",
            output.to_cli_string(),
            "--slate-data",
            json.dumps(slate_data),
        ]
        if timecode_ref_path is not None:
            args.extend(["--timecode-ref", str(timecode_ref_path)])
        if user_settings.letterbox is not None and output.use_letterbox:
            args.extend(["--letterbox", str(user_settings.letterbox)])

        process.run(
            self.nuke_path,
            args,
        )

        self.logger.info(
            f"Finished rendering preview to {output_preview_path}."
        )

    def _deliver_sequence(
        self,
        shot: Shot,
        version: Version,
        delivery_sequence_path: Path,
        show_validation_error,
        show_validation_message,
        update_progress,
    ):
        should_rerender = False
        output = next(
            (
                output
                for output in self.settings.delivery_sequence_outputs
                if output.status == version.sequence_output_status
            ),
            None,
        )

        if output is not None:
            if output.settings.keys() == ["compression"]:
                metadata = parse_exr_metadata.read_exr_header(
                    version.sequence_path % version.first_frame
                )
                if "compression" in metadata:
                    if (
                        output.settings["compression"].lower()
                        in metadata.get("compression")
                        .replace("_COMPRESSION", "")
                        .lower()
                    ):
                        self.logger.info("Match compression")
                    else:
                        should_rerender = True
            else:
                should_rerender = True

        # Create sequence delivery folder
        sequence_delivery_folder = delivery_sequence_path.parent
        self.logger.info(
            f"Creating folder for delivery {sequence_delivery_folder}."
        )
        sequence_delivery_folder.mkdir(parents=True, exist_ok=True)

        if should_rerender or self.settings.add_slate_to_sequence:
            publish_file = Path(version.sequence_path)

            first_frame = version.first_frame
            if version.frames_have_slate:
                first_frame += 1

            args = [
                "-t",
                self.plate_path,
                str(first_frame),
                str(version.last_frame),
                publish_file.as_posix(),
                delivery_sequence_path.as_posix(),
            ]

            render_name = "main"
            if output is not None:
                render_name = f"{output.status} - {output.name}"

                version.validation_message = (
                    f"Rerendering frames for {render_name}..."
                )
                show_validation_message(version)

                args.extend(
                    [
                        "--write-settings",
                        (output.to_cli_string() if output is not None else {}),
                    ]
                )

            process = NukeProcess(
                version,
                show_validation_error,
                show_validation_message,
                update_progress,
                render_name,
            )

            if self.settings.add_slate_to_sequence:
                slate_data = self._get_slate_data(version, shot)

                args.extend(
                    [
                        "--logo-path",
                        self.logo_path,
                        "-odt",
                        self.settings.preview_colorspace_odt,
                        "--slate-data",
                        json.dumps(slate_data),
                        "--font-path",
                        self.font_path,
                        "--font-bold-path",
                        self.font_bold_path,
                    ]
                )

                if not should_rerender:
                    args.append("--slate-only")

            process.run(
                self.nuke_path,
                args,
            )
        if not should_rerender:
            version.validation_message = "Delivering frames..."
            show_validation_message(version)

            can_link = False
            if (
                Path(version.sequence_path).drive
                == delivery_sequence_path.drive
            ):
                can_link = True

            first_frame = version.first_frame
            if version.frames_have_slate:
                first_frame += 1

            for frame in range(first_frame, version.last_frame + 1):
                publish_file = Path(version.sequence_path % frame)
                delivery_file = delivery_sequence_path.with_name(
                    delivery_sequence_path.name % frame
                )

                if can_link:
                    os.link(publish_file, delivery_file)
                else:
                    shutil.copyfile(publish_file, delivery_file)

                update_progress(
                    (frame - first_frame) / (version.last_frame - first_frame)
                )

            self.logger.info(
                f"Finished linking {version.sequence_path} to {delivery_sequence_path}."
            )

    def _deliver_attachment(
        self,
        version: Version,
        user_settings: UserSettings,
        delivery_folder: Path,
    ):
        if version.attachment is not None and (
            any(
                value == ("version", "attachment")
                for key, value in user_settings.csv_fields
            )
        ):
            name = version.attachment["name"]
            if version.attachment["link_type"] == "upload":
                url = version.attachment["url"]
                urlretrieve(url, delivery_folder / name)
            elif version.attachment["link_type"] == "local":
                file_path = None
                if sgtk.util.is_linux():
                    file_path = version.attachment["local_path_linux"]
                elif sgtk.util.is_macos():
                    file_path = version.attachment["local_path_mac"]
                elif sgtk.util.is_windows():
                    file_path = version.attachment["local_path_windows"]

                if file_path is not None:
                    shutil.copyfile(file_path, delivery_folder / name)

    def export_versions(
        self,
        user_settings: UserSettings,
        show_validation_error: Callable[[Version], None],
        update_progress_bars: Callable[[Version], None],
        show_validation_message: Callable[[Version], None],
        finish_export_versions: Callable[[], None],
        get_deliverables: Callable[[Version], Deliverables],
    ) -> None:
        """Starts the shot export thread.

        Args:
            user_settings: User settings
            show_validation_error: Function for showing validation errors
            update_progress_bars: Function for updating progress bars
            show_validation_message: Function for showing validation messages
            finish_export_versions: Function for updating GUI when export is done
            get_deliverables: Function for getting the selected delivery options
        """
        self.export_shots_thread = ExportShotsThread(
            self,
            user_settings,
            show_validation_error,
            update_progress_bars,
            show_validation_message,
            finish_export_versions,
            get_deliverables,
        )
        self.export_shots_thread.start()

    def _get_slate_data(self, version, shot):
        """
        Compile the slate data object

        Args:
            version (Version): Version to use
            shot (Shot): Shot to use
        """
        episode = ""
        scene = ""
        if shot.episode is not None:
            episode = shot.episode
            scene = ""
        elif "_" in shot.sequence:
            episode, scene = shot.sequence.split("_")

        optional_fields = self.settings.get_slate_extra_fields(
            self.get_version_template_fields(shot, version)
        )

        return {
            "version_name": f"v{version.version_number:03d}",
            "submission_note": version.submission_note,
            "submitting_for": version.submitting_for,
            "shot_name": shot.code,
            "shot_types": version.task.name,
            "vfx_scope_of_work": shot.description,
            "show": self.get_project()["name"],
            "episode": episode,
            "scene": scene,
            "sequence_name": shot.sequence,
            "vendor": self.base_template_fields["vnd"],
            "input_has_slate": version.movie_has_slate,
            "optional_fields": optional_fields,
        }

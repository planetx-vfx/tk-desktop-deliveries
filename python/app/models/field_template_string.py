from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

import sgtk

from ..external import parse_exr_metadata
from . import util
from .util import EXR_COMPRESSION

if TYPE_CHECKING:
    from .context import Context
    from .shotgrid_cache import ShotGridCache

logger = sgtk.platform.get_logger(__name__)


class FieldTemplateString:
    template: str
    fields = list[str]
    ordered_fields = dict[str, str]
    cache: ShotGridCache | None

    def __init__(self, template: str, cache: ShotGridCache | None = None):
        self.template = str(template)
        self._repr_template = self.template.replace("<", "＜").replace(
            ">", "＞"
        )

        self.fields = self._extract_fields()

        self.ordered_fields = self._order_fields()

        self.cache = cache

        if not self.validate():
            msg = 'Validation of field template string "%s" failed.'
            raise Exception(msg, template)

    def validate(self, allowed_entities: list[str] | None = None):
        success = True

        if self.template == "":
            return True

        if allowed_entities is None:
            allowed_entities = [
                "file",
                "project",
                "shot",
                "version",
                "date",
            ]

        logger.debug(
            'Validating template "%s":',
            self._repr_template,
        )
        logger.debug("  Fields: %s", ", ".join(self.fields))

        for field in self.fields:
            if "." in field:
                entry = field.split(".")

                entity = entry[0]
                field_name = ".".join(entry[1:])

                if entity in allowed_entities:
                    if entity == "file":
                        if field_name not in [
                            "name",
                            "name_ranged",
                            "codec",
                            "compression",
                            "bit_depth",
                            "folder",
                        ]:
                            logger.debug(
                                '  Field "%s" is not available for a file entity.',
                                entity,
                            )
                            success = False
                        continue

                    if entity in [
                        "project",
                        "shot",
                        "version",
                    ]:
                        if self.cache is not None:
                            entity_name = entity[0].upper() + entity[1:]
                            field_base = field_name.split(".")[0]
                            if field_base not in [
                                *self.cache.fields.get(entity_name, []),
                                "code",
                                "description",
                            ]:
                                logger.debug(
                                    '  Field "%s" could not be found in "%s".',
                                    field_name,
                                    entity,
                                )
                                success = False
                        else:
                            logger.debug(
                                '  Field "%s" of entity "%s" could not be checked. Ignoring.',
                                field_name,
                                entity,
                            )
                        continue

                    # TODO date validation

                else:
                    logger.debug('  Entity "%s" not allowed.', entity)
                    success = False
            else:
                logger.debug("  Field only provided an entity.")
                success = False

        return success

    def apply_context(self, context: Context):
        if context.file is None and "file" in self.ordered_fields:
            logger.debug("Context: %s", context.as_dict())
            msg = f'No file context supplied for resolving field template string "{self.template}".'
            raise Exception(msg)

        project = next(
            project
            for project in context.cache.get_raw("Project")
            if project["id"] == context.cache.context.project["id"]
        )
        version = None
        shot = None

        if context.entity is not None:
            if context.entity.get("type") == "Version":
                logger.debug("Got version from provided entity.")
                version = next(
                    (
                        version
                        for version in context.cache.get_raw("Version")
                        if version["id"] == context.entity["id"]
                    ),
                    None,
                )
            if context.entity.get("type") == "Shot":
                logger.debug("Got shot from provided entity.")
                shot = next(
                    (
                        shot
                        for shot in context.cache.get_raw("Shot")
                        if shot["id"] == context.entity["id"]
                    ),
                    None,
                )

        if version is None and context.version is not None:
            version = next(
                (
                    v
                    for v in context.cache.get_raw("Version")
                    if v["id"] == context.version.id
                ),
                None,
            )
            if version is None:
                logger.debug(
                    "Couldn't resolve version from provided version: %s",
                    context.version,
                )
            else:
                logger.debug("Got version from provided context.")

        if "version" in self.ordered_fields and version is None:
            logger.debug("Context: %s", context.as_dict())
            msg = f'No version context supplied for resolving field template string "{self.template}".'
            raise Exception(msg)

        if version is not None and version["entity"]["type"] == "Shot":
            shot = next(
                (
                    s
                    for s in context.cache.get_raw("Shot")
                    if s["id"] == version["entity"]["id"]
                ),
                None,
            )
            if shot is None:
                logger.debug(
                    "Couldn't resolve shot from resolved version: %s",
                    context.version,
                )
            else:
                logger.debug("Got shot from resolved version.")
        if shot is None and context.shot is not None:
            shot = next(
                (
                    s
                    for s in context.cache.get_raw("shot")
                    if s["id"] == context.shot.id
                ),
                None,
            )
            if version is None:
                logger.debug(
                    "Couldn't resolve shot from provided shot: %s",
                    context.shot,
                )
            else:
                logger.debug("Got shot from provided context.")

        if "shot" in self.ordered_fields and shot is None:
            logger.debug("Context: %s", context.as_dict())
            msg = f'No shot context supplied for resolving field template string "{self._repr_template}".'
            raise Exception(msg)

        # Fix footage format links
        if shot is not None:
            large_map = {
                ff["id"]: ff
                for ff in context.cache.get(
                    context.cache.settings.footage_format_entity
                )
            }
            shot[context.cache.settings.shot_footage_formats_field] = [
                large_map[i["id"]]
                for i in shot[
                    context.cache.settings.shot_footage_formats_field
                ]
                if i["id"] in large_map
            ]

        sg_data = {
            "project": project,
            "shot": shot,
            "version": version,
        }
        template = self.template

        for entity, fields in self.ordered_fields.items():
            for field in fields:
                logger.debug("%s: %s", entity, field)
                field_value = None
                if entity == "file":
                    file_name = context.file.file_path.name
                    output_file_path = context.file.file_path.as_posix()
                    if field == "name":
                        field_value = file_name
                    elif field == "name_ranged":
                        new_file_name = file_name

                        # Extract frame pattern and replace with frame range
                        frame_pattern = re.compile(r"(%0(\d)d)")
                        frame_match = re.search(frame_pattern, new_file_name)
                        if frame_match:
                            full_frame_spec = frame_match.group(1)

                            first_frame = context.version.first_frame
                            if context.file.has_slate:
                                first_frame -= 1

                            new_file_name = new_file_name.replace(
                                full_frame_spec,
                                f"[{first_frame}-{context.version.last_frame}]",
                            )

                        field_value = new_file_name

                    if field in ("codec", "compression"):
                        if (
                            context.file.codec is not None
                            and context.file.codec != ""
                        ):
                            field_value = context.file.codec

                        elif file_name.endswith(".exr"):
                            try:
                                metadata = parse_exr_metadata.read_exr_header(
                                    output_file_path
                                    % context.version.last_frame
                                )
                                if "compression" in metadata:
                                    field_value = EXR_COMPRESSION.get(
                                        metadata["compression"],
                                        "unknown",
                                    )
                                else:
                                    field_value = ""
                            except:
                                field_value = ""
                    elif field == "bit_depth":
                        if (
                            context.file.bit_depth is not None
                            and context.file.bit_depth != ""
                        ):
                            field_value = context.file.bit_depth
                        elif file_name.endswith(".exr"):
                            try:
                                metadata = parse_exr_metadata.read_exr_header(
                                    output_file_path
                                    % context.version.last_frame
                                )
                                channels = metadata.get("channels", {})
                                if len(channels) > 0:
                                    pixel_type = next(iter(channels.values()))[
                                        "pixel_type"
                                    ]
                                    bit_depths = {
                                        0: "32-bit uint",
                                        1: "16-bit half",
                                        2: "32-bit float",
                                    }
                                    field_value = bit_depths.get(
                                        pixel_type, ""
                                    )
                                else:
                                    field_value = ""
                            except:
                                field_value = ""
                        else:
                            field_value = ""
                    if field == "folder":
                        field_value = context.file.directory_path.name

                elif entity == "version" and field == (
                    context.cache.settings.attachment_field
                ):
                    if (
                        context.version.attachment is not None
                        and context.version.attachment["link_type"]
                        in ["upload", "local"]
                    ):
                        field_value = context.version.attachment["name"]
                    else:
                        field_value = ""

                elif entity == "date":
                    date = datetime.now()
                    # Try to format the date
                    try:
                        field_value = date.strftime(field)
                    except Exception as err:
                        msg = f'Failed to convert date to format "{entity}.{field}".'
                        raise Exception(msg) from err

                elif entity in sg_data and sg_data[entity] is not None:
                    try:
                        value = util.get_nested_value(
                            field, sg_data[entity], True
                        )
                        if value is None:
                            logger.error(
                                'Template field value "%s" is empty for %s %s',
                                field,
                                entity,
                                sg_data[entity]["id"],
                            )
                            field_value = ""
                        else:
                            field_value = value
                    except:
                        logger.error(
                            'Template field value "%s" could not be found in %s.',
                            field,
                            entity,
                        )
                        logger.debug(sg_data[entity])
                        field_value = None

                if field_value is not None:
                    template = template.replace(
                        f"<{entity}.{field}>", str(field_value)
                    )
                else:
                    msg = (
                        f'Failed to resolve template field: "{entity}.{field}"'
                    )
                    raise Exception(msg)

        return template

    def _extract_fields(self):
        """
        Extract all fields wrapped in <…> where a field may contain
        letters, digits, underscores and dots.
        """
        return re.findall(r"<([\w.%]+)>", self.template)

    def _order_fields(self):
        ordered_fields = {}

        for field in self.fields:
            entry = field.split(".")
            if entry[0] in ordered_fields:
                ordered_fields[entry[0]].append(".".join(entry[1:]))
            else:
                ordered_fields[entry[0]] = [".".join(entry[1:])]

        return ordered_fields

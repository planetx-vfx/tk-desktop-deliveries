"""ShotGrid Review
Netherlands Filmacademy 2022

Will use Nuke to automatically create a slate
with Netherlands Filmacademy design, transcode it
and upload to ShotGrid
"""

#  MIT License
#
#  Copyright (c) 2024 Netherlands Film Academy
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

from __future__ import annotations

from pathlib import Path

import nuke
import shotgun_api3
import os
import re


class ShotGridSlate(object):
    """Creates slate provided by publish data, transcodes and
    uploads to ShotGrid.

    Args:
            first_frame (int): first frame from frame sequence
            last_frame (int): first frame from frame sequence
            sequence_path (str): path to frame sequence
            slate_path (str): path to render slate
            shotgrid_site (str): url for ShotGrid site
            script_name (str): API name for script on ShotGrid
            script_key (str): API key for script on ShotGrid
            logo_path (str): Path to company logo
            fps (float, optional): fps used by project. Defaults to 25.0.
            company (str, optional): company name to add to slate. Defaults to "ShotGrid".
            colorspace_idt (str, optional): Input colorspace. Defaults to "ACES - ACEScg".
            colorspace_odt (str, optional): Output colorspace. Defaults to "Output - sRGB".
            publish_id (int): Publish id of published file to link to the version.
            version_id (int): Version id to update. When not specified, a new version will be created.
    """

    def __init__(
        self,
        first_frame,
        last_frame,
        sequence_path,
        slate_path,
        shotgrid_site,
        script_name,
        script_key,
        logo_path: str,
        fps=25.0,
        company="ShotGrid",
        colorspace_idt="ACES - ACEScg",
        colorspace_odt="Output - sRGB",
        publish_id: int = None,
        version_id: int = None,
        font_path: str = None,
        font_bold_path: str = None,
    ):
        self.first_frame = first_frame
        self.last_frame = last_frame
        self.sequence_path = sequence_path.replace(os.sep, "/")
        self.slate_path = slate_path.replace(os.sep, "/")
        self.shotgrid_site = shotgrid_site
        self.script_name = script_name
        self.script_key = script_key
        self.logo_path = logo_path
        self.fps = fps
        self.company = company
        self.colorspace_idt = colorspace_idt
        self.colorspace_odt = colorspace_odt
        self.publish_id = publish_id
        self.version_id = version_id
        self.font_path = font_path
        self.font_bold_path = font_bold_path

        # Get script directory to add gizmo
        script_directory = os.path.dirname(os.path.realpath(__file__))
        node_path = os.path.abspath(
            os.path.join(script_directory, "..", "..", "resources", "slate.nk")
        )
        node_path = node_path.replace(os.sep, "/")

        # Setting connection to ShotGrid with API
        self.sg = shotgun_api3.Shotgun(
            shotgrid_site, script_name=script_name, api_key=script_key
        )

        # If is a video
        if sequence_path.endswith(".mov"):
            sequence = True
        else:
            # Get frame sequences by path
            sequence = self.__validate_sequence(sequence_path)

        # If sequence is found, proceed
        if sequence:
            read = self.__setup_script()

            if self.version_id is not None:
                self.entity_type = "Version"
                self.entity_id = self.version_id
            else:
                msg = "Version ID not provided. Canceling slate creation."
                raise Exception(msg)

            # Create slate
            slate = self.__setup_slate(
                read_node=read,
                slate_node_path=node_path,
            )

            # Create write node
            write = self.__setup_write(
                slate_node=slate,
            )

            # Render slate
            self.__render_slate(
                write_node=write,
            )
        else:
            msg = "Sequence not found, aborting!"
            raise Exception(msg)

    def __validate_sequence(
        self,
        sequence_path,
    ):
        """Check if sequence is existing

        Args:
            sequence_path (str): sequence to check

        Returns:
            str or False: if validated returns sequence containing frame list
        """
        sequence_directory = os.path.dirname(sequence_path)
        sequence_filename = os.path.basename(sequence_path)

        sequences = self.__get_frame_sequences(sequence_directory)

        for sequence in sequences:
            filename = os.path.basename(sequence[0])

            if "1001" in filename:
                print("Found incorrectly filename, fixing frame padding")
                filename = filename.replace("1001", "%04d")

            if sequence_filename == filename:
                return sequence

        raise Exception("No frame sequence found")

    def __setup_script(self):
        """Creates Nuke script with read node and correct settings

        Returns:
            attribute: created read node
        """
        # Setup Nuke script
        nuke.root().knob("first_frame").setValue(self.first_frame)
        nuke.root().knob("last_frame").setValue(self.last_frame)
        nuke.root().knob("fps").setValue(self.fps)
        nuke.root().knob("colorManagement").setValue("OCIO")
        nuke.root().knob("OCIO_config").setValue(0)

        print("Setup script completed")

        # Setup read node
        read = nuke.createNode("Read")
        read.knob("file").setValue(self.sequence_path)

        # first_sequence_frame = int(min(sequence[1]))
        # last_sequence_frame = int(max(sequence[1]))
        frame_in = 1
        frame_out = self.last_frame - self.first_frame + frame_in

        # Set found frame range by sequence find function
        read.knob("first").setValue(frame_in)
        read.knob("origfirst").setValue(frame_in)
        read.knob("last").setValue(frame_out)
        read.knob("origlast").setValue(frame_out)

        read.knob("frame_mode").setValue(1)
        read.knob("frame").setValue(str(self.first_frame))

        read.knob("colorspace").setValue(self.colorspace_idt)
        read.knob("on_error").setValue("checkerboard")

        print("Created read node")

        # Return created read node
        return read

    def __get_publish_data(self):
        """Search ShotGrid database for associated publish data

        Returns:
            dict: containing all publish data

            E.g.:
            {
                "type": "PublishedFile",
                "id": 42421,
                "created_by": {
                    "id": 1,
                    "name": "Example User",
                    "type": "HumanUser",
                },
                "code": "iwr_pri_pri_0030_scene_main_v014.%04d.exr",
                "task": {"id": 24136, "name": "comp", "type": "Task"},
                "project": {"id": 2602, "name": "it_will_rain",
                            "type": "Project"},
                "entity": {"id": 7193, "name": "pri_0030", "type": "Shot"},
                "description": "Integrated DMP",
                "version_number": 14,
            }
        """
        # Create the filter to search on ShotGrid
        # for publishes with the same file name
        filters = [
            ["id", "is", self.publish_id],
        ]

        columns = [
            "created_by",
            "code",
            "task",
            "project",
            "entity",
            "description",
            "version_number",
        ]

        # Search on ShotGrid
        publish = self.sg.find_one("PublishedFile", filters, columns)

        print("Got publish data")

        return publish

    def __get_version_data(
        self,
    ):
        """Search ShotGrid database for associated version data

        Returns:
            dict: containing all version data
        """
        # Create the filter to search on ShotGrid
        # for publishes with the same file name
        filters = [
            ["id", "is", self.version_id],
        ]

        columns = [
            "created_by",
            "code",
            "sg_task",
            "project",
            "entity",
            "description",
            "version_number",
            "sg_delivery_note",
            "sg_submitting_for",
            "published_files",
        ]

        # Search on ShotGrid
        version = self.sg.find_one("Version", filters, columns)

        print("Got version data")

        return version

    def __get_shot_data(self, version: dict):
        """Search ShotGrid database for associated version data

        Returns:
            dict: containing all version data
        """
        # Create the filter to search on ShotGrid
        # for publishes with the same file name
        filters = [
            ["id", "is", version["entity"]["id"]],
        ]

        columns = [
            "code",
            "sg_cut_in",
            "sg_cut_out",
            "sg_cut_duration",
            "sg_episode",
            "sg_submitting_for",
            "sg_delivery_note",
            "description",
            "sg_sequence",
        ]

        # Search on ShotGrid
        version = self.sg.find_one("Shot", filters, columns)

        print("Got shot data")

        return version

    def __get_project_data(self) -> dict | None:
        """
        Get project data from task or entity.
        Returns:
            dict | None: Project data
        """
        if self.entity_type is not None and self.entity_id is not None:
            entity = self.sg.find_one(
                self.entity_type, [["id", "is", self.entity_id]], ["project"]
            )
            if not entity:
                return None
            return self.sg.find_one(
                "Project",
                [["id", "is", entity["project"]["id"]]],
                ["name", "sg_vendorid"],
            )
        else:
            return None

    def __get_task_data(self) -> dict | None:
        """
        Get entity data from task.
        Returns:
            dict | None: User data
        """
        if (
            self.entity_type is not None
            and self.entity_type == "Task"
            and self.entity_id is not None
        ):
            task = self.sg.find_one(
                "Task", [["id", "is", self.entity_id]], ["name"]
            )
            return task
        else:
            return None

    def __get_entity_data_from_task(self) -> dict | None:
        """
        Get entity data from task.
        Returns:
            dict | None: User data
        """
        if (
            self.entity_type is not None
            and self.entity_type == "Task"
            and self.entity_id is not None
        ):
            task = self.sg.find_one(
                "Task", [["id", "is", self.entity_id]], ["entity"]
            )
            return task.get("entity")
        else:
            return None

    def __setup_slate(
        self,
        read_node,
        slate_node_path: str,
    ):
        """Setup slate with correct parameters

        Args:
            read_node (attribute): read node to connect slate to
            slate_node_path (str): path to slate node Nuke file

        Returns:
            attribute: created slate node
        """

        # Create slate node
        nuke.nodePaste(slate_node_path)

        for node in nuke.selectedNodes():
            node["selected"].setValue(False)

        logo = nuke.toNode("LOGO")

        logo.knob("file").setValue(self.logo_path)

        slate = nuke.toNode("NETFLIX_TEMPLATE_SLATE")

        sg_project = self.__get_project_data()
        sg_version = self.__get_version_data()
        sg_shot = self.__get_shot_data(sg_version)
        # sg_task = self.__get_task_data()

        version_number = 0
        if len(sg_version["published_files"]):
            self.publish_id = sg_version["published_files"][0]["id"]
            sg_publish = self.__get_publish_data()
            version_number = sg_publish["version_number"]

        # print(sg_project)
        # print(sg_version)
        # print(sg_shot)

        slate["shotName"].setValue(Path(sg_version["code"]).name)

        slate["f_version_name"].setValue(f"v{version_number:04d}")
        slate["f_submission_note"].setValue(sg_version["sg_delivery_note"])
        slate["f_submitting_for"].setValue(sg_version["sg_submitting_for"])

        slate["f_shot_name"].setValue(sg_shot["code"])
        if sg_version["sg_task"]:
            slate["f_shot_types"].setValue(sg_version["sg_task"]["name"])
        slate["f_vfx_scope_of_work"].setValue(sg_shot["description"])

        slate["f_show"].setValue(sg_project["name"])

        slate["f_frames_first"].setValue(
            sg_shot["sg_cut_in"]
            if sg_shot["sg_cut_in"] is not None
            else self.last_frame - 1
        )
        slate["f_frames_last"].setValue(
            sg_shot["sg_cut_out"]
            if sg_shot["sg_cut_out"] is not None
            else self.last_frame
        )

        slate.knob("active_frame").setValue(self.first_frame - 1)
        slate.knob("thumbnail_frame").setValue(
            int((self.first_frame + self.last_frame) / 2)
        )

        # Manual AddTimeCode fix
        time = slate.node("AddTimeCode1")
        time.knob("startcode").setValue("0")
        time.knob("frame").setValue(self.first_frame)

        # TODO Actual episode implementation
        if "_" in sg_shot["sg_sequence"]["name"]:
            episode, scene = sg_shot["sg_sequence"]["name"].split("_")
            slate["f_episode"].setValue(episode)
            slate["f_scene"].setValue(scene)
        slate["f_sequence_name"].setValue(sg_shot["sg_sequence"]["name"])

        slate.knob("f_media_color").setValue(
            self.colorspace_odt.replace("Output - ", "")
        )

        if sg_project["sg_vendorid"]:
            slate["f_vendor"].setValue(sg_project["sg_vendorid"])

        # Set fonts
        slate.knob("font").setValue(self.font_path)
        slate.knob("font_bold").setValue(self.font_bold_path)

        # Set read node as input for slate node
        slate.setInput(0, read_node)

        # Return created node
        return slate

    def __setup_write(self, slate_node):
        """Create write node with correct settings

        Args:
            slate_node (attribute): node to connect write node to

        Returns:
            attribute: created write node
        """

        # Create write node
        write = nuke.createNode("Write")
        # Set write node settings
        write.knob("file").setValue(self.slate_path)
        write.knob("file_type").setValue("mov")
        write.knob("mov64_codec").setValue(14)  # H.264
        write.knob("colorspace").setValue(self.colorspace_odt)
        write.knob("afterFrameRender").setValue(
            "print(f\"Frame {nuke.frame()} ({int(nuke.frame() - nuke.root().knob('first_frame').value() + 1)} of {int(nuke.root().knob('last_frame').value() - nuke.root().knob('first_frame').value() + 1)})\")"
        )

        # Set input
        write.setInput(0, slate_node)

        # Create directories
        slate_directory = os.path.dirname(self.slate_path)
        if not os.path.isdir(slate_directory):
            print("Slate directory doesn't exist, creating one")
            os.makedirs(slate_directory)

        return write

    def __render_slate(
        self,
        write_node,
    ):
        """Render specified write node

        Args:
            write_node (attribute): write node to render
        """

        try:
            nuke.execute(write_node, self.first_frame - 1, self.last_frame)
            print("Rendering complete")

        except Exception as error:
            print("Could not render because %s" % str(error))

    @staticmethod
    def __get_frame_sequences(
        folder,
        extensions=None,
        frame_spec=None,
    ):
        """
        Copied from the publisher plugin, and customized to return file
        sequences with frame lists instead of filenames
        Given a folder, inspect the contained files to find what appear to be
        files with frame numbers.
        :param folder: The path to a folder potentially containing a
        sequence of
            files.
        :param extensions: A list of file extensions to retrieve paths for.
            If not supplied, the extension will be ignored.
        :param frame_spec: A string to use to represent the frame number in the
            return sequence path.
        :return: A list of tuples for each identified frame sequence. The first
            item in the tuple is a sequence path with the frame number replaced
            with the supplied frame specification. If no frame spec is
            supplied,
            a python string format spec will be returned with the padding found
            in the file.
            Example::
            get_frame_sequences(
                "/path/to/the/folder",
                ["exr", "jpg"],
                frame_spec="{FRAME}"
            )
            [
                (
                    "/path/to/the/supplied/folder/key_light1.{FRAME}.exr",
                    [<frame_1_framenumber>, <frame_2_framenumber>, ...]
                ),
                (
                    "/path/to/the/supplied/folder/fill_light1.{FRAME}.jpg",
                    [<frame_1_framenumber>, <frame_2_framenumber>, ...]
                )
            ]
        """
        FRAME_REGEX = re.compile(r"(.*)([._-])(\d+)\.([^.]+)$", re.IGNORECASE)

        # list of already processed file names
        processed_names = {}

        # examine the files in the folder
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)

            if os.path.isdir(file_path):
                # ignore subfolders
                continue

            # see if there is a frame number
            frame_pattern_match = re.search(FRAME_REGEX, filename)

            if not frame_pattern_match:
                # no frame number detected. carry on.
                continue

            prefix = frame_pattern_match.group(1)
            frame_sep = frame_pattern_match.group(2)
            frame_str = frame_pattern_match.group(3)
            extension = frame_pattern_match.group(4) or ""

            # filename without a frame number.
            file_no_frame = "%s.%s" % (prefix, extension)

            if file_no_frame in processed_names:
                # already processed this sequence. add the framenumber to the
                # list, later we can use this to determine the framerange
                processed_names[file_no_frame]["frame_list"].append(frame_str)
                continue

            if extensions and extension not in extensions:
                # not one of the extensions supplied
                continue

            # make sure we maintain the same padding
            if not frame_spec:
                padding = len(frame_str)
                frame_spec = "%%0%dd" % (padding,)

            seq_filename = "%s%s%s" % (prefix, frame_sep, frame_spec)

            if extension:
                seq_filename = "%s.%s" % (seq_filename, extension)

            # build the path in the same folder
            seq_path = os.path.join(folder, seq_filename)

            # remember each seq path identified and a
            # list of files matching the
            # seq pattern
            processed_names[file_no_frame] = {
                "sequence_path": seq_path,
                "frame_list": [frame_str],
            }

        # build the final list of sequence paths to return
        frame_sequences = []
        for file_no_frame in processed_names:
            seq_info = processed_names[file_no_frame]
            seq_path = seq_info["sequence_path"]

            frame_sequences.append((seq_path, seq_info["frame_list"]))

        return frame_sequences
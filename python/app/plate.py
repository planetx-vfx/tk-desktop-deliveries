#  MIT License
#
#  Copyright (c) 2024 Planet X
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

import json
import os
import re
from pathlib import Path

import PyOpenColorIO as OCIO
import nuke


class PlateRender(object):
    """Rerender a plate"""

    first_frame: int
    last_frame: int
    input_path: str
    output_path: str
    write_settings: dict = {}
    logo_path: str | None
    colorspace_odt: str
    slate_data: dict | None = None
    font_path: str = None
    font_bold_path: str = None
    slate_only: bool = False

    def __init__(
        self,
        first_frame,
        last_frame,
        input_path,
        output_path,
        write_settings: str = None,
        logo_path: str = None,
        colorspace_odt: str = "ACES - ACES2065-1",
        slate_data: str = None,
        font_path: str = None,
        font_bold_path: str = None,
        slate_only: bool = False,
    ):
        """Rerender a plate with new settings

        Args:
                first_frame (int): first frame from frame sequence
                last_frame (int): last frame from frame sequence
                input_path (str): path to frame sequence
                output_path (str): path to render sequence
                write_settings (str): JSON string of the write node's settings
                slate_data (str): JSON string of the slate settings, if none no slate will be rendered
        """
        self.first_frame = first_frame
        self.last_frame = last_frame
        self.first_render_frame = first_frame
        self.input_path = input_path.replace(os.sep, "/")
        self.output_path = output_path.replace(os.sep, "/")

        if write_settings is not None:
            try:
                self.write_settings: dict = json.loads(write_settings)
            except:
                msg = f"Invalid write settings. ({write_settings})"
                print(msg)

        # Slate
        self.render_slate = (
            logo_path is not None
            and colorspace_odt is not None
            and font_path is not None
            and font_bold_path is not None
            and slate_data is not None
        )
        if self.render_slate:
            self.logo_path = logo_path
            self.colorspace_odt = colorspace_odt
            self.font_path = font_path
            self.font_bold_path = font_bold_path
            self.slate_only = slate_only

            if slate_data is not None:
                try:
                    self.slate_data = json.loads(slate_data)
                    self.first_render_frame -= 1
                except:
                    msg = f"Invalid slate data. ({slate_data})"
                    raise Exception(msg)

        # Cancel if input is a video
        if self.input_path.endswith(".mov"):
            msg = f"Input path is a movie file and is unsupported."
            raise Exception(msg)

        # Get frame sequences by path
        sequence = self.__validate_sequence(self.input_path)

        # If sequence is found, proceed
        if sequence:
            read = self.__setup_script()

            write_input = read
            if self.render_slate:
                # Get script directory to add gizmo
                script_directory = os.path.dirname(os.path.realpath(__file__))
                node_path = os.path.abspath(
                    os.path.join(
                        script_directory, "..", "..", "resources", "slate.nk"
                    )
                )
                node_path = node_path.replace(os.sep, "/")

                slate = self.__setup_slate(read, node_path)

                write_input = slate

                if write_settings is None:
                    compression = read.metadata().get("exr/compressionName")
                    if compression is not None:
                        self.write_settings["compression"] = compression

            # Create write node
            write = self.__setup_write(
                input_node=write_input,
            )

            # Render plate
            self.__render(
                write_node=write,
            )
        else:
            msg = f"Sequence not found, aborting! ({self.input_path})"
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
        sequence_path = Path(sequence_path)
        sequence_directory = sequence_path.parent
        sequence_filename = sequence_path.name

        sequences = self.__get_frame_sequences(
            sequence_directory, [sequence_path.suffix[1:]]
        )

        for sequence in sequences:
            filename = os.path.basename(sequence[0])

            if "1001" in filename:
                print("Found incorrectly filename, fixing frame padding")
                filename = filename.replace("1001", "%04d")

            if sequence_filename == filename:
                return sequence

        raise Exception(f"No frame sequence found in {sequence_directory}")

    def __setup_script(self):
        """Creates Nuke script with read node and correct settings

        Returns:
            attribute: created read node
        """
        # Setup Nuke script
        nuke.root().knob("first_frame").setValue(self.first_render_frame)
        nuke.root().knob("last_frame").setValue(self.last_frame)

        print("Setup script completed")

        # Setup read node
        read = nuke.nodes.Read(file=self.input_path)

        read.knob("first").setValue(self.first_frame)
        read.knob("last").setValue(self.last_frame)
        read.knob("origfirst").setValue(self.first_frame)
        read.knob("origlast").setValue(self.last_frame)

        read.knob("raw").setValue(True)
        read.knob("on_error").setValue("checkerboard")

        print("Created read node")

        # Return created read node
        return read

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

        input = nuke.toNode("INPUT")
        add_timecode = nuke.toNode("AddTimeCode")
        slate = nuke.toNode("NETFLIX_TEMPLATE_SLATE")

        # Set read node as input for slate node
        input.setInput(0, read_node)

        timecode = nuke.nodes.Read(file=self.input_path)
        timecode["name"].setValue("Timecode")
        timecode["first"].setValue(self.first_frame)
        timecode["last"].setValue(self.last_frame)
        timecode["origfirst"].setValue(self.first_frame)
        timecode["origlast"].setValue(self.last_frame)

        add_timecode.knob("frame").setValue(self.first_frame)

        if (
            add_timecode.metadata("input/timecode", self.first_frame)
            == "00:00:00:00"
        ):
            time = slate.node("AddTimeCode1")
            time.knob("startcode").setValue("0")
            time.knob("frame").setValue(self.first_frame)

        if self.logo_path.endswith(".nk"):
            logo = nuke.nodePaste(self.logo_path)

            for node in nuke.selectedNodes():
                node["selected"].setValue(False)

            slate.setInput(1, logo)
        else:
            logo = nuke.nodes.Read(file=self.logo_path)
            premult = nuke.nodes.Premult()
            premult.setInput(0, logo)

            slate.setInput(1, premult)

        slate["f_version_name"].setValue(self.slate_data["version_name"])
        slate["f_submission_note"].setValue(self.slate_data["submission_note"])
        slate["f_submitting_for"].setValue(self.slate_data["submitting_for"])
        slate["f_shot_name"].setValue(self.slate_data["shot_name"])
        slate["f_shot_types"].setValue(self.slate_data["shot_types"])
        slate["f_vfx_scope_of_work"].setValue(
            self.slate_data["vfx_scope_of_work"]
        )
        slate["f_sequence_name"].setValue(self.slate_data["sequence_name"])
        slate["f_vendor"].setValue(self.slate_data["vendor"])
        slate["f_show"].setValue(self.slate_data["show"])

        if self.slate_data["episode"] != "":
            slate["f_episode"].setValue(self.slate_data["episode"])
        if self.slate_data["scene"] != "":
            slate["f_scene"].setValue(self.slate_data["scene"])

        slate["f_frames_first"].setValue(self.first_frame - 1)
        slate["f_frames_last"].setValue(self.last_frame)

        slate.knob("active_frame").setValue(self.first_frame - 1)
        slate.knob("thumbnail_frame").setValue(
            int((self.first_frame + self.last_frame) / 2)
        )

        # Get correct colorspace
        colorspace_odt = self.colorspace_odt
        if "OCIO" in os.environ:
            config = OCIO.GetCurrentConfig()
            roles = [
                role
                for role in config.getRoles()
                if role[0] == self.colorspace_odt
            ]
            if len(roles) > 0:
                colorspace_odt = roles[0][1]

        slate.knob("f_media_color").setValue(colorspace_odt)

        # Optional Fields, max 6
        if "optional_fields" in self.slate_data:
            for i, (key, value) in enumerate(
                list(self.slate_data["optional_fields"].items())[0:6]
            ):
                slate[f"f_opt{i+1}_key"].setValue(key)
                slate[f"f_opt{i+1}_value"].setValue(value)

        # Set fonts
        slate.knob("font").setValue(self.font_path)
        slate.knob("font_bold").setValue(self.font_bold_path)

        # Return created node
        return slate

    def __setup_write(self, input_node):
        """Create write node with correct settings

        Args:
            input_node (attribute): node to connect write node to

        Returns:
            attribute: created write node
        """

        # Create write node
        write = nuke.createNode("Write")
        # Set write node settings
        write.knob("file").fromUserText(self.output_path)
        write.knob("raw").setValue(True)
        write.knob("afterFrameRender").setValue(
            "print(f\"Frame {nuke.frame()} ({int(nuke.frame() - nuke.root().knob('first_frame').value() + 1)} of {int(nuke.root().knob('last_frame').value() - nuke.root().knob('first_frame').value() + 1)})\")"
        )

        if "file_type" in self.write_settings:
            write.knob("file_type").setValue(self.write_settings["file_type"])

        for knob, setting in self.write_settings.items():
            try:
                write[knob].setValue(setting)
            except Exception as e:
                print(
                    f"Could not apply {setting} to the knob {knob}, because {e}"
                )

        # Set input
        write.setInput(0, input_node)

        # Create directories
        slate_directory = os.path.dirname(self.output_path)
        if not os.path.isdir(slate_directory):
            print("Slate directory doesn't exist, creating one")
            os.makedirs(slate_directory)

        return write

    def __render(
        self,
        write_node,
    ):
        """Render specified write node

        Args:
            write_node (attribute): write node to render
        """

        try:
            nuke.execute(
                write_node,
                self.first_render_frame,
                (
                    self.first_render_frame
                    if self.slate_only
                    else self.last_frame
                ),
            )
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

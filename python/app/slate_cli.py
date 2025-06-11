from slate import ShotGridSlate

import argparse

parser = argparse.ArgumentParser(
    description="Render a slate and add/update a version on ShotGrid."
    "Make sure the last argument is not a number!",
)

parser.add_argument("first_frame", type=int)
parser.add_argument("last_frame", type=int)
parser.add_argument("fps", type=float)
parser.add_argument("sequence_path", type=str)
parser.add_argument("slate_path", type=str)
parser.add_argument("logo_path", type=str)

parser.add_argument(
    "-idt",
    "--colorspace-idt",
    default="ACES - ACEScg",
    type=str,
    metavar="colorspace",
)
parser.add_argument(
    "-odt",
    "--colorspace-odt",
    default="Output - sRGB",
    type=str,
    metavar="colorspace",
)
parser.add_argument(
    "--timecode-ref", type=str, help="Path to sequence with correct timecode"
)
parser.add_argument(
    "-lb",
    "--letterbox",
    type=str,
    help="Letterbox overlay settings. Format: <width>:<height>/<opacity>",
)
parser.add_argument(
    "-ws",
    "--write-settings",
    type=str,
    help="Settings for the write node as a JSON object",
)
parser.add_argument(
    "-slate",
    "--slate-data",
    type=str,
    help="JSON data of slate data.",
)

parser.add_argument(
    "--new-submission-note",
    action="store_true",
    help="If a new submission note should be added from slate data.",
)

fonts = parser.add_argument_group("Fonts")
fonts.add_argument(
    "--font-path",
    type=str,
    help="Path to the regular font.",
)
fonts.add_argument(
    "--font-bold-path",
    type=str,
    help="Path to the bold font.",
)

args = parser.parse_args()

print(f"Starting slate with the following data: {vars(args)}")

ShotGridSlate(**vars(args))

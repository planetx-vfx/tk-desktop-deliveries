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
parser.add_argument("shotgrid_site", type=str)
parser.add_argument("script_name", type=str)
parser.add_argument("script_key", type=str)
parser.add_argument("logo_path", type=str)

parser.add_argument(
    "-c", "--company", default="ShotGrid", type=str, metavar="name"
)
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

shotgrid = parser.add_argument_group("ShotGrid")
shotgrid.add_argument(
    "--publish-id",
    type=int,
    metavar="id",
    help="Publish id of published file to link to the version.",
)
shotgrid.add_argument(
    "--version-id",
    type=int,
    metavar="id",
    help="Version id on ShotGrid to update. If none is provided, a new version will be created.",
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

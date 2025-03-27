from plate import PlateRender

import argparse

parser = argparse.ArgumentParser(
    description="Rerender a plate and add a slate frame on ShotGrid."
    "Make sure the last argument is not a number!",
)

parser.add_argument("first_frame", type=int)
parser.add_argument("last_frame", type=int)
parser.add_argument("input_path", type=str)
parser.add_argument("output_path", type=str)

parser.add_argument(
    "-ws",
    "--write-settings",
    type=str,
    help="Settings fro the write node as a JSON object",
)

slate = parser.add_argument_group("Slate")
slate.add_argument(
    "-logo",
    "--logo-path",
    type=str,
    help="Path to logo.",
)
slate.add_argument(
    "-odt",
    "--colorspace-odt",
    default="Output - sRGB",
    type=str,
    metavar="colorspace",
)
slate.add_argument(
    "-slate",
    "--slate-data",
    type=str,
    help="JSON data of slate data.",
)
slate.add_argument(
    "--font-path",
    type=str,
    help="Path to the regular font.",
)
slate.add_argument(
    "--font-bold-path",
    type=str,
    help="Path to the bold font.",
)
slate.add_argument(
    "--slate-only",
    action="store_true",
    help="Only output the slate.",
)

args = parser.parse_args()

print(f"Starting rerender with the following data: {vars(args)}")

PlateRender(**vars(args))

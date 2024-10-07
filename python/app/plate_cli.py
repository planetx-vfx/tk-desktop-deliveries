from plate import PlateRender

import argparse

parser = argparse.ArgumentParser(
    description="Render a slate and add/update a version on ShotGrid."
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

args = parser.parse_args()

print(f"Starting rerender with the following data: {vars(args)}")

PlateRender(**vars(args))

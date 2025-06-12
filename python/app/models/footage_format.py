import json
from enum import Enum

import sgtk

logger = sgtk.platform.get_logger(__name__)


class FootageFormatType(Enum):
    INPUT_ONLINE = "Input Online"
    INPUT_OFFLINE = "Input Offline"
    INPUT_OTHER = "Input Other"
    OUTPUT_RENDER = "Output Render"
    OUTPUT_PREVIEW = "Output Preview"
    OUTPUT_OTHER = "Output Other"
    DELIVERY = "Delivery"


class FootageFormat:
    footage_type: FootageFormatType
    resolution: str
    width: int
    height: int
    crop: str
    aspect_ratio: str
    pixel_aspect_ratio: str
    frame_rate: str
    video_bit_depth: str
    video_codec: str

    name: str
    id: int

    def __init__(
        self,
        footage_type: str,
        resolution: str,
        crop: str,
        aspect_ratio: str,
        pixel_aspect_ratio: str,
        frame_rate: str,
        video_bit_depth: str,
        video_codec: str,
        id: int = None,
        name: str = None,
    ):
        self.id = id
        self.name = name
        self.footage_type = FootageFormatType(footage_type)
        self.resolution = resolution
        self.crop = crop
        self.aspect_ratio = aspect_ratio
        self.pixel_aspect_ratio = pixel_aspect_ratio
        self.frame_rate = frame_rate
        self.video_bit_depth = video_bit_depth
        self.video_codec = video_codec

        try:
            self.width = int(resolution.split("x")[0])
            self.height = int(resolution.split("x")[1])
            if aspect_ratio is None:
                self.aspect_ratio = f"{(self.width/self.height):.2f}"
        except Exception as err:
            msg = f"An error occurred while creating a footage format: {err}"
            logger.error(msg)

    def get_crop(self):
        if self.crop is None:
            return 0, 0

        if "," in self.crop:
            x, y = self.crop.split(",")
            return int(x), int(y)
        else:
            return int(self.crop), int(self.crop)

    @staticmethod
    def from_sg(mapping: dict, data: dict):
        mapped_data = {"name": data.get("code"), "id": data.get("id")}

        for key, value in mapping.items():
            mapped_data[key] = data.get(value)

        return FootageFormat(**mapped_data)

    def as_dict(self) -> dict:
        return {
            "footage_type": self.footage_type.name,
            "resolution": self.resolution,
            "crop": self.crop,
            "aspect_ratio": self.aspect_ratio,
            "pixel_aspect_ratio": self.pixel_aspect_ratio,
            "frame_rate": self.frame_rate,
            "video_bit_depth": self.video_bit_depth,
            "video_codec": self.video_codec,
        }

    def __str__(self):
        return json.dumps(self.as_dict())

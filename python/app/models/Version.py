from __future__ import annotations


class Version:
    id: int
    id_str: str
    code: str
    first_frame: int
    last_frame: int
    fps: int
    version_number: int
    thumbnail: str
    sequence_path: str | None
    path_to_movie: str | None
    task: Task | None
    submitting_for: str
    delivery_note: str

    deliver_preview: bool
    deliver_sequence: bool

    sequence_output_status: str

    validation_message: str | None
    validation_error: str | None
    progress: float

    def __init__(
        self,
        id: int,
        code: str,
        first_frame: int,
        last_frame: int,
        fps: int,
        version_number: int,
        thumbnail: str,
        sequence_path: str,
        path_to_movie: str,
        task: Task = None,
        submitting_for: str = "",
        delivery_note: str = "",
        attachment: dict = None,
        deliver_preview: bool = True,
        deliver_sequence: bool = True,
        sequence_output_status: str = "",
    ):
        self.id = id
        self.id_str = str(id)
        self.code = code
        self.first_frame = first_frame
        self.last_frame = last_frame
        self.fps = fps
        self.version_number = version_number
        self.thumbnail = thumbnail

        if sequence_path and sequence_path != "":
            self.sequence_path = sequence_path
        else:
            self.sequence_path = None

        if path_to_movie and path_to_movie != "":
            self.path_to_movie = path_to_movie
        else:
            self.path_to_movie = None

        self.task = task
        self.submitting_for = submitting_for
        self.delivery_note = delivery_note
        self.attachment = attachment

        self.deliver_preview = deliver_preview
        self.deliver_sequence = deliver_sequence

        self.sequence_output_status = sequence_output_status

        self.validation_message = ""
        self.validation_error = ""
        self.progress = 0


class Task:
    id: int
    name: str

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

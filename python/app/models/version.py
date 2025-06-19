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
    frames_have_slate: bool
    movie_has_slate: bool
    task: Task | None
    submitting_for: str
    submission_note: str
    submission_note_short: str

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
        frames_have_slate: bool = False,
        movie_has_slate: bool = False,
        task: Task = None,
        submitting_for: str = "",
        submission_note: str = "",
        submission_note_short: str = "",
        attachment: dict | None = None,
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
        self.version_number = max(0, int(version_number))
        self.thumbnail = thumbnail
        self.frames_have_slate = frames_have_slate
        self.movie_has_slate = movie_has_slate

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
        self.submission_note = submission_note
        self.submission_note_short = submission_note_short
        self.attachment = attachment

        self.deliver_preview = deliver_preview
        self.deliver_sequence = deliver_sequence

        self.sequence_output_status = sequence_output_status

        self.validation_message = ""
        self.validation_error = ""
        self.progress = 0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "id_str": self.id_str,
            "code": self.code,
            "first_frame": self.first_frame,
            "last_frame": self.last_frame,
            "fps": self.fps,
            "version_number": self.version_number,
            "thumbnail": self.thumbnail,
            "sequence_path": self.sequence_path,
            "path_to_movie": self.path_to_movie,
            "frames_have_slate": self.frames_have_slate,
            "movie_has_slate": self.movie_has_slate,
            "task": (
                self.task.as_dict() if self.task is not None else "undefined"
            ),
            "submitting_for": self.submitting_for,
            "submission_note": self.submission_note,
            "submission_note_short": self.submission_note_short,
            "deliver_preview": self.deliver_preview,
            "deliver_sequence": self.deliver_sequence,
            "sequence_output_status": self.sequence_output_status,
            "validation_message": self.validation_message,
            "validation_error": self.validation_error,
            "progress": self.progress,
        }

    def get(self, key: str):
        """
        Return the value for key if key is in the dictionary, else default.
        """
        return self.as_dict().get(key)


class Task:
    id: int
    name: str

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }

    def get(self, key: str):
        """
        Return the value for key if key is in the dictionary, else default.
        """
        return self.as_dict().get(key)

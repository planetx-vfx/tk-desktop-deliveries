class Letterbox:
    width: float
    height: float
    opacity: float

    def __init__(self, width: float, height: float, opacity: float):
        self.width = width
        self.height = height
        self.opacity = opacity

    def __str__(self):
        return f"{self.width}:{self.height}/{self.opacity}"

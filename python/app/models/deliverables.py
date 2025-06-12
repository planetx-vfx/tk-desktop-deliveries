class Deliverables:
    deliver_sequence: bool
    deliver_preview: bool

    def __init__(self, deliver_sequence: bool, deliver_preview: bool):
        self.deliver_sequence = deliver_sequence
        self.deliver_preview = deliver_preview

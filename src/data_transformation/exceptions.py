class TransformationError(Exception):

    def __init__(
        self, message: str, step: str | None = None, record_count: int | None = None
    ):
        self.step = step
        self.record_count = record_count
        super().__init__(message)

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.step:
            parts.append(f"step={self.step}")
        if self.record_count is not None:
            parts.append(f"records={self.record_count}")
        return " | ".join(parts)

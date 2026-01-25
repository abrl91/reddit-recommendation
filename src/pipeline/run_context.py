from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class RunContext:

    run_id: str
    started_at: datetime

    @classmethod
    def create(cls) -> "RunContext":
        return cls(run_id=str(uuid4()), started_at=datetime.now(UTC))

from contextlib import contextmanager
from typing import Generator

from .exceptions import TransformationError


@contextmanager
def pipeline_step(
    step_name: str, record_count: int | None = None
) -> Generator[None, None, None]:
    try:
        yield
    except TransformationError:
        raise  # this is already wrapped. don't double-wrap
    except Exception as e:
        raise TransformationError(
            f"Failed during {step_name}: {e}",
            step=step_name,
            record_count=record_count,
        ) from e

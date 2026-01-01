from collections.abc import Callable
from datetime import UTC, datetime
from functools import reduce

from ..models import SubredditCleaned, SubredditData, SubredditListingResponse

TransformFn = Callable[[SubredditCleaned], SubredditCleaned]


def _pipe(data: SubredditCleaned, steps: list[TransformFn]) -> SubredditCleaned:
    """Apply a sequence of transform functions to data."""
    return reduce(lambda d, fn: fn(d), steps, data)


def _extract_nested_data(response: SubredditListingResponse) -> list[SubredditCleaned]:
    """Extract subreddits from nested API response structure."""
    results: list[SubredditCleaned] = []

    for child in response["data"]["children"]:
        raw: SubredditData = child["data"]
        cleaned = SubredditCleaned(
            subreddit_name=raw.get("display_name", ""),
            title=raw.get("title", ""),
            description=raw.get("public_description", ""),
            subscribers=raw.get("subscribers", 0),
            is_nsfw=raw.get("over18", False),
            url=raw.get("url", ""),
            created_date=str(raw.get("created_utc", 0)),
        )
        results.append(cleaned)

    return results


def _normalize_fields(data: SubredditCleaned) -> SubredditCleaned:
    """Normalize field values (e.g., prepend reddit.com to URL)."""
    return data.model_copy(
        update={"url": f"https://reddit.com{data.url}"}
    )


def _convert_timestamps(data: SubredditCleaned) -> SubredditCleaned:
    """Convert Unix timestamp to ISO 8601 date string."""
    try:
        unix_ts = float(data.created_date or 0)
        iso_date = datetime.fromtimestamp(unix_ts, tz=UTC).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        iso_date = ""

    return data.model_copy(update={"created_date": iso_date})


def _add_metadata(data: SubredditCleaned) -> SubredditCleaned:
    """Add processing metadata (timestamp)."""
    return data.model_copy(
        update={"processed_at": datetime.now(UTC).isoformat()}
    )


def _remove_nulls(data: SubredditCleaned) -> SubredditCleaned:
    """Replace None values with sensible defaults."""
    updates: dict[str, str] = {}

    if data.created_date is None:
        updates["created_date"] = ""
    if data.processed_at is None:
        updates["processed_at"] = ""

    return data.model_copy(update=updates) if updates else data


def _validate_data_quality(data: SubredditCleaned) -> SubredditCleaned:
    """Validate required fields. Raises ValueError if invalid, returns data if valid."""
    if not data.subreddit_name:
        raise ValueError("subreddit_name is required")
    return data


CLEANUP_PIPELINE: list[TransformFn] = [
    _normalize_fields,
    _convert_timestamps,
    _add_metadata,
    _remove_nulls,
    _validate_data_quality,
]


def clean_row_data(
    raw_data: list[SubredditListingResponse],
) -> list[SubredditCleaned]:
    """Main entry point: transform raw API responses through the pipeline."""
    results: list[SubredditCleaned] = []

    for response in raw_data:
        for item in _extract_nested_data(response):
            clean_data = _pipe(item, CLEANUP_PIPELINE)
            results.append(clean_data)

    return results



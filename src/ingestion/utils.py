import httpx
import structlog

from src.ingestion.exceptions import IngestionError
from src.models.reddit import (
    SubredditChild,
    SubredditData,
    SubredditListingResponse,
)

logger = structlog.get_logger().bind(module="ingestion")

REDDIT_BASE_URL = "https://www.reddit.com"
DEFAULT_HEADERS = {"User-Agent": "reddit-recommendation/1.0"}
DEFAULT_TIMEOUT = 30


def make_request(url: str) -> dict:
    """Make HTTP request with error handling. Raises IngestionError on failure."""
    logger.info("Fetching from Reddit API", url=url)

    try:
        response = httpx.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
    except httpx.RequestError as e:
        raise IngestionError(f"Network error fetching {url}") from e

    if response.status_code != 200:
        raise IngestionError(
            f"Reddit API returned status {response.status_code}: {response.text[:200]}"
        )

    logger.info("Reddit API response received", status_code=response.status_code)
    return response.json()


def extract_subreddits_from_posts(posts_response: dict) -> SubredditListingResponse:
    """
    Extract sr_detail from each post, dedupe by display_name.
    Normalizes to SubredditListingResponse format for consistent bronze storage.
    """
    seen: dict[str, SubredditData] = {}

    children = posts_response.get("data", {}).get("children", [])
    for child in children:
        post_data = child.get("data", {})
        sr_detail: SubredditData | None = post_data.get("sr_detail")

        if sr_detail is None:
            continue

        display_name = sr_detail.get("display_name")
        if display_name and display_name not in seen:
            seen[display_name] = sr_detail

    subreddit_children: list[SubredditChild] = [
        {"kind": "t5", "data": sr_data} for sr_data in seen.values()
    ]

    result: SubredditListingResponse = {
        "kind": "Listing",
        "data": {"children": subreddit_children},
    }

    logger.info(
        "Extracted subreddits from posts",
        total_posts=len(children),
        unique_subreddits=len(subreddit_children),
    )

    return result

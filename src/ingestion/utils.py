import httpx
import structlog

from src.ingestion.exceptions import IngestionError
from src.ingestion.reddit_auth import (
    REDDIT_OAUTH_BASE_URL,
    REDDIT_PUBLIC_BASE_URL,
    get_oauth_headers,
    get_public_headers,
    has_oauth_credentials,
)
from src.models.reddit import (
    SubredditChild,
    SubredditData,
    SubredditListingResponse,
)

logger = structlog.get_logger().bind(module="ingestion")

DEFAULT_TIMEOUT = 30

_use_oauth: bool | None = None


def _should_use_oauth() -> bool:
    global _use_oauth
    if _use_oauth is None:
        _use_oauth = has_oauth_credentials()
        if _use_oauth:
            logger.info("OAuth credentials found, using authenticated API")
        else:
            logger.info(
                "No OAuth credentials, using public API (residential IP only)")
    return _use_oauth


def get_base_url() -> str:
    return REDDIT_OAUTH_BASE_URL if _should_use_oauth() else REDDIT_PUBLIC_BASE_URL


def make_request(url: str) -> dict:
    logger.info("Fetching from Reddit API", url=url)

    use_oauth = _should_use_oauth()
    headers = get_oauth_headers() if use_oauth else get_public_headers()

    try:
        response = httpx.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    except httpx.RequestError as e:
        raise IngestionError(f"Network error fetching {url}") from e

    if response.status_code != 200:
        raise IngestionError(
            f"Reddit API returned status {response.status_code}: {response.text[:200]}"
        )

    logger.info("Reddit API response received",
                status_code=response.status_code)
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

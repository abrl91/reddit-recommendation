import httpx
import structlog

from src.data_ingestion.exceptions import IngestionError
from src.models.reddit import SubredditListingResponse

logger = structlog.get_logger().bind(module="ingestion")


def fetch_popular_subreddits() -> SubredditListingResponse:
    url = "https://www.reddit.com/subreddits/popular.json"
    headers = {"User-Agent": "reddit-recommendation/1.0"}

    logger.info("Fetching from Reddit API", url=url)

    try:
        response = httpx.get(url, headers=headers, timeout=30)
    except httpx.RequestError as e:
        raise IngestionError(f"Network error fetching {url}") from e

    if response.status_code != 200:
        raise IngestionError(
            f"Reddit API returned status {response.status_code}: {response.text[:200]}"
        )

    logger.info("Reddit API response received",
                status_code=response.status_code)
    popular_subreddits: SubredditListingResponse = response.json()
    return popular_subreddits

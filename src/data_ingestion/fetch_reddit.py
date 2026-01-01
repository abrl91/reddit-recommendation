from typing import Any

import httpx

from .exceptions import IngestionError


def fetch_popular_subreddits() -> dict[str, Any]:
    """Raises IngestionError on failure."""
    url = "https://www.reddit.com/subreddits/popular.json"
    headers = {"User-Agent": "reddit-recommendation/1.0"}

    try:
        response = httpx.get(url, headers=headers, timeout=30)
    except httpx.RequestError as e:
        raise IngestionError(f"Network error fetching {url}") from e

    if response.status_code != 200:
        raise IngestionError(
            f"Reddit API returned status {response.status_code}: {response.text[:200]}"
        )

    return response.json()

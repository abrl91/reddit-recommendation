import httpx
import structlog

from src.ingestion.exceptions import IngestionError

logger = structlog.get_logger().bind(module="ingestion")

DEFAULT_TIMEOUT = 30


def make_request(url: str) -> dict:
    logger.info("Fetching from Lemmy API", url=url)

    try:
        response = httpx.get(url, timeout=DEFAULT_TIMEOUT, follow_redirects=True)
    except httpx.RequestError as e:
        raise IngestionError(f"Network error fetching {url}") from e

    if response.status_code != 200:
        raise IngestionError(
            f"Lemmy API returned status {response.status_code}: {response.text[:200]}"
        )

    logger.info("Lemmy API response received", status_code=response.status_code)
    return response.json()

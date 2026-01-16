import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
import structlog

from src.ingestion.exceptions import IngestionError

logger = structlog.get_logger().bind(module="reddit_auth")

REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_BASE_URL = "https://oauth.reddit.com"
REDDIT_PUBLIC_BASE_URL = "https://www.reddit.com"

USER_AGENT = "linux:recommenddit:v1.0.0 (by /u/PianoLong8618)"

# Token will be refreshed 5 minutes before expiry
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


@dataclass
class RedditToken:
    access_token: str
    expires_at: datetime


_cached_token: RedditToken | None = None


def get_credentials() -> tuple[str, str] | None:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")

    if client_id and client_secret:
        return client_id, client_secret
    return None


def has_oauth_credentials() -> bool:
    return get_credentials() is not None


def _fetch_new_token() -> RedditToken:
    credentials = get_credentials()
    if credentials is None:
        raise IngestionError(
            "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set in environment"
        )

    client_id, client_secret = credentials
    headers = {"User-Agent": USER_AGENT}
    data = {"grant_type": "client_credentials"}

    logger.info("Fetching new Reddit OAuth token")

    try:
        response = httpx.post(
            REDDIT_TOKEN_URL,
            auth=(client_id, client_secret),
            data=data,
            headers=headers,
            timeout=30,
        )
    except httpx.RequestError as e:
        raise IngestionError(f"Network error fetching OAuth token: {e}") from e

    if response.status_code != 200:
        raise IngestionError(
            f"Failed to get OAuth token: {response.status_code} - {response.text[:200]}"
        )

    token_data = response.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", 3600)

    if not access_token:
        raise IngestionError(f"No access_token in response: {token_data}")

    expires_at = datetime.now() + timedelta(seconds=expires_in)
    logger.info("Got new Reddit OAuth token", expires_in=expires_in)

    return RedditToken(access_token=access_token, expires_at=expires_at)


def get_access_token() -> str:
    global _cached_token

    if _cached_token is not None:
        if datetime.now() < (_cached_token.expires_at - TOKEN_REFRESH_BUFFER):
            return _cached_token.access_token
        logger.info("Token expired or expiring soon, refreshing")

    _cached_token = _fetch_new_token()
    return _cached_token.access_token


def get_oauth_headers() -> dict[str, str]:
    token = get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
    }


def get_public_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}

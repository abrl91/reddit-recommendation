from typing import Any
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.models import LemmyListingResponse, LemmyPostResponse


@pytest.fixture
def sample_community_data() -> dict[str, Any]:
    """Single community record as returned by Lemmy API."""
    return {
        "community": {
            "id": 1,
            "name": "python",
            "title": "Python Programming",
            "description": "News about Python",
            "nsfw": False,
            "actor_id": "https://lemmy.world/c/python",
            "published": "2023-01-01T12:00:00Z",
        },
        "counts": {
            "subscribers": 1500000,
        },
    }


@pytest.fixture
def sample_community_response(
    sample_community_data: dict[str, Any],
) -> LemmyListingResponse:
    """Valid Lemmy API response with one community."""
    return {"communities": [sample_community_data]}


@pytest.fixture
def sample_post_data() -> dict[str, Any]:
    """Single post record as returned by Lemmy API."""
    return {
        "post": {
            "id": 123,
            "name": "Test Post Title",
            "body": "This is the post body",
            "url": "https://example.com/article",
            "published": "2023-06-15T10:30:00Z",
        },
        "community": {
            "id": 1,
            "name": "python",
        },
        "creator": {
            "id": 42,
        },
        "counts": {
            "score": 150,
            "comments": 25,
        },
    }


@pytest.fixture
def sample_post_response(sample_post_data: dict[str, Any]) -> LemmyPostResponse:
    """Valid Lemmy API response with one post."""
    return {"posts": [sample_post_data]}


@pytest.fixture
def sample_extracted_community_df() -> pl.DataFrame:
    """DataFrame as it looks after extraction from API response."""
    return pl.DataFrame(
        {
            "community_name": ["python", "learnpython"],
            "title": ["Python Programming", "Learn Python"],
            "description": ["News about Python", "Subreddit for learning Python"],
            "subscribers": [1500000, 800000],
            "is_nsfw": [False, False],
            "url": [
                "https://lemmy.world/c/python",
                "https://lemmy.world/c/learnpython",
            ],
            "published_date": ["2023-01-01T12:00:00Z", "2023-02-01T12:00:00Z"],
            "instance": ["lemmy.world", "lemmy.world"],
        }
    )


@pytest.fixture
def mock_s3_client(mocker: Any) -> MagicMock:
    """Mocked boto3 S3 client."""
    mock_client = MagicMock()
    mocker.patch("boto3.client", return_value=mock_client)
    return mock_client

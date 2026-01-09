from typing import Any
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.models.reddit import SubredditListingResponse


@pytest.fixture
def sample_subreddit_data() -> dict[str, Any]:
    """Single subreddit record as returned by Reddit API."""
    return {
        "display_name": "Python",
        "title": "Python Programming",
        "public_description": "News about Python",
        "subscribers": 1500000,
        "over18": False,
        "url": "/r/Python/",
        "created_utc": 1234567890.0,
    }


@pytest.fixture
def sample_subreddit_response(sample_subreddit_data: dict[str, Any]) -> SubredditListingResponse:
    """Valid Reddit API response with one subreddit."""
    return {
        "kind": "Listing",
        "data": {
            "children": [
                {"kind": "t5", "data": sample_subreddit_data}
            ]
        }
    }


@pytest.fixture
def sample_subreddit_response_multiple() -> SubredditListingResponse:
    """Reddit API response with multiple subreddits for testing extraction."""
    return {
        "kind": "Listing",
        "data": {
            "children": [
                {
                    "kind": "t5",
                    "data": {
                        "display_name": "Python",
                        "title": "Python Programming",
                        "public_description": "News about Python",
                        "subscribers": 1500000,
                        "over18": False,
                        "url": "/r/Python/",
                        "created_utc": 1234567890.0,
                    }
                },
                {
                    "kind": "t5",
                    "data": {
                        "display_name": "learnpython",
                        "title": "Learn Python",
                        "public_description": "Subreddit for learning Python",
                        "subscribers": 800000,
                        "over18": False,
                        "url": "/r/learnpython/",
                        "created_utc": 1300000000.0,
                    }
                },
            ]
        }
    }


@pytest.fixture
def sample_extracted_dataframe() -> pl.DataFrame:
    """DataFrame as it looks after extraction from API response."""
    return pl.DataFrame({
        "subreddit_name": ["Python", "learnpython"],
        "title": ["Python Programming", "Learn Python"],
        "description": ["News about Python", "Subreddit for learning Python"],
        "subscribers": [1500000, 800000],
        "is_nsfw": [False, False],
        "url": ["/r/Python/", "/r/learnpython/"],
        "created_date": [1234567890.0, 1300000000.0],
    })


@pytest.fixture
def mock_s3_client(mocker: Any) -> MagicMock:
    """Mocked boto3 S3 client."""
    mock_client = MagicMock()
    mocker.patch("boto3.client", return_value=mock_client)
    return mock_client

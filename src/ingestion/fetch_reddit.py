from typing import cast

from src.ingestion.utils import (
    REDDIT_BASE_URL,
    extract_subreddits_from_posts,
    make_request,
)
from src.models.reddit import SubredditListingResponse


def fetch_popular_subreddits() -> SubredditListingResponse:
    """Fetch /subreddits/popular.json - top subreddits by subscriber count."""
    url = f"{REDDIT_BASE_URL}/subreddits/popular.json"
    return cast(SubredditListingResponse, make_request(url))


def fetch_new_subreddits() -> SubredditListingResponse:
    """Fetch /subreddits/new.json - newly created subreddits."""
    url = f"{REDDIT_BASE_URL}/subreddits/new.json"
    return cast(SubredditListingResponse, make_request(url))


def fetch_hot_subreddits() -> SubredditListingResponse:
    """
    Fetch /r/popular/hot.json?sr_detail=true, extract unique subreddits.
    Returns normalized SubredditListingResponse format.
    """
    url = f"{REDDIT_BASE_URL}/r/popular/hot.json?sr_detail=true"
    posts_response = make_request(url)
    return extract_subreddits_from_posts(posts_response)


def fetch_rising_subreddits() -> SubredditListingResponse:
    """
    Fetch /r/popular/rising.json?sr_detail=true, extract unique subreddits.
    Returns normalized SubredditListingResponse format.
    """
    url = f"{REDDIT_BASE_URL}/r/popular/rising.json?sr_detail=true"
    posts_response = make_request(url)
    return extract_subreddits_from_posts(posts_response)

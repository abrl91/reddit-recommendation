from typing import cast

from src.ingestion.utils import (
    extract_subreddits_from_posts,
    get_base_url,
    make_request,
)
from src.models.reddit import SubredditListingResponse


def fetch_popular_subreddits() -> SubredditListingResponse:
    """Fetch /subreddits/popular.json - top subreddits by subscriber count."""
    url = f"{get_base_url()}/subreddits/popular.json"
    return cast(SubredditListingResponse, make_request(url))


def fetch_new_subreddits() -> SubredditListingResponse:
    """Fetch /subreddits/new.json - newly created subreddits."""
    url = f"{get_base_url()}/subreddits/new.json"
    return cast(SubredditListingResponse, make_request(url))


def fetch_hot_subreddits() -> SubredditListingResponse:
    """
    Fetch /r/popular/hot.json?sr_detail=true, extract unique subreddits.
    Returns normalized SubredditListingResponse format.
    """
    url = f"{get_base_url()}/r/popular/hot.json?sr_detail=true"
    posts_response = make_request(url)
    return extract_subreddits_from_posts(posts_response)


def fetch_rising_subreddits() -> SubredditListingResponse:
    """
    Fetch /r/popular/rising.json?sr_detail=true, extract unique subreddits.
    Returns normalized SubredditListingResponse format.
    """
    url = f"{get_base_url()}/r/popular/rising.json?sr_detail=true"
    posts_response = make_request(url)
    return extract_subreddits_from_posts(posts_response)

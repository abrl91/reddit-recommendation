from enum import StrEnum
from typing import TypedDict


class SourceTag(StrEnum):
    """Source tags for subreddit data origin."""

    POPULAR = "popular"
    NEW = "new"
    HOT = "hot"
    RISING = "rising"


class SubredditData(TypedDict, total=False):
    """Subreddit data from Reddit API. Using total=False since API returns many more fields."""

    display_name: str
    title: str
    subscribers: int
    public_description: str
    created_utc: float
    url: str
    subreddit_type: str
    id: str
    name: str
    over18: bool


class SubredditChild(TypedDict):
    kind: str
    data: SubredditData


class SubredditListingData(TypedDict):
    children: list[SubredditChild]


class SubredditListingResponse(TypedDict):
    kind: str
    data: SubredditListingData

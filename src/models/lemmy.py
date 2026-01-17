from typing import TypedDict


# --- Raw API structures (nested, as returned by Lemmy API) ---


class RawCommunity(TypedDict, total=False):
    id: int
    name: str
    title: str
    description: str
    nsfw: bool
    published: str
    actor_id: str


class RawCounts(TypedDict, total=False):
    subscribers: int
    score: int
    comments: int


class RawCreator(TypedDict, total=False):
    id: int


class RawPost(TypedDict, total=False):
    id: int
    name: str
    body: str
    url: str
    published: str


class RawCommunityView(TypedDict, total=False):
    community: RawCommunity
    counts: RawCounts


class RawPostView(TypedDict, total=False):
    post: RawPost
    community: RawCommunity
    creator: RawCreator
    counts: RawCounts


class RawListingResponse(TypedDict):
    communities: list[RawCommunityView]


class RawPostResponse(TypedDict):
    posts: list[RawPostView]


# --- Normalized/flattened structures (after transformation) ---


class CommunityData(TypedDict):
    id: int
    name: str
    title: str
    description: str
    subscribers: int
    nsfw: bool
    published: str
    url: str
    instance: str


class PostData(TypedDict):
    id: int
    name: str
    body: str | None
    url: str | None
    community_id: int
    community_name: str
    creator_id: int
    published: str
    score: int
    num_comments: int


class LemmyListingResponse(TypedDict):
    communities: list[CommunityData]


class LemmyPostResponse(TypedDict):
    posts: list[PostData]

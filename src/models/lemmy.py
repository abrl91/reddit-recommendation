from typing import TypedDict


# --- Raw API structures (nested, as returned by Lemmy API) ---


class RawCommunity(TypedDict, total=False):
    id: int
    name: str
    title: str
    description: str
    removed: bool
    published: str
    updated: str
    deleted: bool
    nsfw: bool
    actor_id: str
    local: bool
    icon: str
    banner: str
    hidden: bool
    posting_restricted_to_mods: bool
    instance_id: int
    visibility: str


class RawPost(TypedDict, total=False):
    id: int
    name: str
    body: str
    url: str
    creator_id: int
    community_id: int
    removed: bool
    locked: bool
    published: str
    updated: str
    deleted: bool
    nsfw: bool
    ap_id: str
    local: bool
    language_id: int
    featured_community: bool
    featured_local: bool
    thumbnail_url: str
    embed_title: str
    embed_description: str


class RawCommunityCounts(TypedDict, total=False):
    community_id: int
    subscribers: int
    posts: int
    comments: int
    published: str
    users_active_day: int
    users_active_week: int
    users_active_month: int
    users_active_half_year: int
    subscribers_local: int


class RawPostCounts(TypedDict, total=False):
    post_id: int
    comments: int
    score: int
    upvotes: int
    downvotes: int
    published: str
    newest_comment_time: str


class RawCreator(TypedDict, total=False):
    id: int
    name: str
    display_name: str
    avatar: str
    banner: str
    banned: bool
    deleted: bool
    bot_account: bool
    published: str
    updated: str
    actor_id: str
    bio: str
    local: bool
    instance_id: int
    matrix_user_id: str


class RawCommunityView(TypedDict, total=False):
    community: RawCommunity
    counts: RawCommunityCounts
    subscribed: str
    blocked: bool
    banned_from_community: bool


class RawPostView(TypedDict, total=False):
    post: RawPost
    community: RawCommunity
    creator: RawCreator
    counts: RawPostCounts
    subscribed: str
    saved: bool
    read: bool
    hidden: bool
    creator_banned_from_community: bool
    banned_from_community: bool
    creator_is_moderator: bool
    creator_is_admin: bool
    creator_blocked: bool
    unread_comments: int


class RawListingResponse(TypedDict):
    communities: list[RawCommunityView]


class RawPostResponse(TypedDict):
    posts: list[RawPostView]
    next_page: str | None


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
    # Activity metrics
    posts_count: int
    comments_count: int
    users_active_week: int
    # Display fields
    icon: str | None
    banner: str | None


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
    # Engagement details
    upvotes: int
    downvotes: int
    # Display/attribution
    creator_name: str
    # Content flags
    nsfw: bool
    featured_community: bool
    featured_local: bool


class LemmyListingResponse(TypedDict):
    communities: list[CommunityData]


class LemmyPostResponse(TypedDict):
    posts: list[PostData]

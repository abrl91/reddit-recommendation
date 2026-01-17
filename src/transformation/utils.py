import structlog

from src.config import get_lemmy_base_url
from src.models.lemmy import (
    CommunityData,
    LemmyListingResponse,
    PostData,
    RawCommunityView,
    RawListingResponse,
    RawPostView,
)

logger = structlog.get_logger().bind(module="transformation")


def _map_community_to_data(comm_view: RawCommunityView) -> CommunityData | None:
    community = comm_view.get("community", {})
    counts = comm_view.get("counts", {})

    if not community:
        return None

    name = community.get("name")
    if not name:
        return None

    actor_id = community.get("actor_id", "")
    instance = get_lemmy_base_url().replace("/api/v3", "").replace("https://", "")

    return {
        "id": community.get("id", 0),
        "name": name,
        "title": community.get("title") or name,
        "description": community.get("description") or "",
        "subscribers": counts.get("subscribers", 0),
        "nsfw": community.get("nsfw", False),
        "published": community.get("published") or "",
        "url": actor_id or "",
        "instance": instance,
    }


def _map_post_to_data(post_view: RawPostView) -> PostData | None:
    post = post_view.get("post", {})
    community = post_view.get("community", {})
    creator = post_view.get("creator", {})
    counts = post_view.get("counts", {})

    if not post or not community:
        return None

    return {
        "id": post.get("id", 0),
        "name": post.get("name") or "",
        "body": post.get("body"),
        "url": post.get("url"),
        "community_id": community.get("id", 0),
        "community_name": community.get("name") or "",
        "creator_id": creator.get("id", 0),
        "published": post.get("published") or "",
        "score": counts.get("score", 0),
        "num_comments": counts.get("comments", 0),
    }


def extract_communities_from_list(response: RawListingResponse) -> LemmyListingResponse:
    seen: dict[str, CommunityData] = {}
    communities = response.get("communities", [])

    for comm_view in communities:
        data = _map_community_to_data(comm_view)
        if data and data["name"] not in seen:
            seen[data["name"]] = data

    return _build_response(list(seen.values()), len(communities))


def _build_response(
    communities: list[CommunityData], total_source_items: int
) -> LemmyListingResponse:
    logger.info(
        "Extracted communities",
        source_items=total_source_items,
        unique_communities=len(communities),
    )
    return {"communities": communities}

from typing import Any, TypeGuard

import polars as pl

from src.config import SourceType
from src.models import RawListingResponse, RawPostResponse
from src.transformation.utils import (
    _map_post_to_data,
    extract_communities_from_list,
)


def _is_post_response(
    response: RawPostResponse | RawListingResponse,
) -> TypeGuard[RawPostResponse]:
    return "posts" in response


def _is_listing_response(
    response: RawPostResponse | RawListingResponse,
) -> TypeGuard[RawListingResponse]:
    return "communities" in response


SchemaDefinition = dict[str, Any]

COMMUNITY_SCHEMA: SchemaDefinition = {
    "community_name": pl.String,
    "title": pl.String,
    "description": pl.String,
    "subscribers": pl.Int64,
    "is_nsfw": pl.Boolean,
    "url": pl.String,
    "published_date": pl.String,
    "instance": pl.String,
}

POST_SCHEMA: SchemaDefinition = {
    "post_id": pl.Int64,
    "title": pl.String,
    "body": pl.String,
    "url": pl.String,
    "community_id": pl.Int64,
    "community_name": pl.String,
    "creator_id": pl.Int64,
    "published_date": pl.String,
    "score": pl.Int64,
    "num_comments": pl.Int64,
}

_COMMUNITY_FIELD_MAPPING = [
    ("name", "community_name", pl.String),
    ("title", "title", pl.String),
    ("description", "description", pl.String),
    ("subscribers", "subscribers", pl.Int64),
    ("nsfw", "is_nsfw", pl.Boolean),
    ("url", "url", pl.String),
    ("published", "published_date", pl.String),
    ("instance", "instance", pl.String),
]

_POST_FIELD_MAPPING = [
    ("id", "post_id", pl.Int64),
    ("name", "title", pl.String),
    ("body", "body", pl.String),
    ("url", "url", pl.String),
    ("community_id", "community_id", pl.Int64),
    ("community_name", "community_name", pl.String),
    ("creator_id", "creator_id", pl.Int64),
    ("published", "published_date", pl.String),
    ("score", "score", pl.Int64),
    ("num_comments", "num_comments", pl.Int64),
]


def _extract_posts(response: RawPostResponse) -> pl.DataFrame:
    posts_data = []
    for p in response.get("posts", []):
        data = _map_post_to_data(p)
        if data:
            posts_data.append(data)

    if not posts_data:
        return pl.DataFrame(schema=POST_SCHEMA)

    df = pl.DataFrame(posts_data)
    selections = []
    existing_cols = set(df.columns)
    for api_field, output_name, dtype in _POST_FIELD_MAPPING:
        if api_field in existing_cols:
            selections.append(pl.col(api_field).cast(dtype).alias(output_name))
        else:
            selections.append(pl.lit(None).cast(dtype).alias(output_name))

    return df.select(selections)


def _extract_communities(response: RawListingResponse) -> pl.DataFrame:
    wrapper = extract_communities_from_list(response)
    communities = wrapper["communities"]

    if not communities:
        return pl.DataFrame(schema=COMMUNITY_SCHEMA)

    df = pl.DataFrame(communities)
    selections = []
    existing_cols = set(df.columns)
    for api_field, output_name, dtype in _COMMUNITY_FIELD_MAPPING:
        if api_field in existing_cols:
            selections.append(pl.col(api_field).cast(dtype).alias(output_name))
        else:
            selections.append(pl.lit(None).cast(dtype).alias(output_name))

    return df.select(selections)


def extract_with_source(
    response: RawPostResponse | RawListingResponse, source: SourceType, tag: str
) -> pl.DataFrame:
    if _is_post_response(response):
        df = _extract_posts(response)
    elif _is_listing_response(response):
        df = _extract_communities(response)
    else:
        raise ValueError("Response must contain 'posts' or 'communities' key")

    source_tag = f"{source}_{tag}"

    if df.is_empty():
        return df.with_columns(pl.lit(None).cast(pl.String).alias("source"))

    return df.with_columns(pl.lit(source_tag).alias("source"))

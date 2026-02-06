from typing import Any

import polars as pl

SchemaDefinition = dict[str, Any]

SILVER_COMMUNITY_SCHEMA: SchemaDefinition = {
    # Base fields (from prepare.py)
    "community_name": pl.String,
    "title": pl.String,
    "description": pl.String,
    "subscribers": pl.Int64,
    "is_nsfw": pl.Boolean,
    "url": pl.String,
    "published_date": pl.String,
    "instance": pl.String,
    "posts_count": pl.Int64,
    "comments_count": pl.Int64,
    "users_active_week": pl.Int64,
    "icon": pl.String,
    "banner": pl.String,
    # Metadata
    "source": pl.String,
    "created_date": pl.String,
    "processed_at": pl.String,
    # Enrichment
    "description_length": pl.Int64,
    "is_active_community": pl.Boolean,
    "age_hours": pl.Float64,
    # Lineage
    "source_file": pl.String,
    "run_id": pl.String,
}

SILVER_POST_SCHEMA: SchemaDefinition = {
    # Base fields
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
    "upvotes": pl.Int64,
    "downvotes": pl.Int64,
    "creator_name": pl.String,
    "is_nsfw": pl.Boolean,
    "featured_community": pl.Boolean,
    "featured_local": pl.Boolean,
    # Metadata
    "source": pl.String,
    "created_date": pl.String,
    "processed_at": pl.String,
    # Enrichment
    "engagement_ratio": pl.Float64,
    "comment_density": pl.Float64,
    "content_type": pl.String,
    "body_length": pl.Int64,
    "age_hours": pl.Float64,
    # Lineage
    "source_file": pl.String,
    "run_id": pl.String,
}

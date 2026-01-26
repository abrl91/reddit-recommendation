from datetime import UTC, datetime

import polars as pl

from src.config import get_active_community_threshold


def enrich_posts(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns([
        # Engagement ratio: 0.0-1.0 quality signal
        (pl.col("upvotes").fill_null(0) /
         (pl.col("upvotes").fill_null(0) + pl.col("downvotes").fill_null(0)))
        .fill_nan(0.5)
        .alias("engagement_ratio"),

        # Comment density: discussion activity relative to popularity
        (pl.col("num_comments").fill_null(0) /
         pl.col("score").fill_null(0).clip(lower_bound=1))
        .alias("comment_density"),

        # Content type based on URL pattern
        pl.when(pl.col("url").is_null() | (pl.col("url") == ""))
        .then(pl.lit("text"))
        .when(pl.col("url").str.contains(r"\.(jpg|jpeg|png|gif|webp)$", literal=False))
        .then(pl.lit("image"))
        .otherwise(pl.lit("link"))
        .alias("content_type"),

        # Body length for embeddings (null-safe)
        pl.col("body").fill_null("").str.len_chars().alias("body_length"),

        # Age in hours since publication
        ((pl.lit(datetime.now(UTC)) - pl.col("published_date").str.to_datetime(time_zone="UTC"))
         .dt.total_hours())
        .alias("age_hours"),
    ])


def enrich_communities(df: pl.DataFrame) -> pl.DataFrame:
    threshold = get_active_community_threshold()
    return df.with_columns([
        # Description length for embeddings
        pl.col("description").fill_null(
            "").str.len_chars().alias("description_length"),

        # Active community flag (configurable threshold)
        (pl.col("users_active_week").fill_null(0)
         > threshold).alias("is_active_community"),

        # Age in hours since creation
        ((pl.lit(datetime.now(UTC)) - pl.col("published_date").str.to_datetime(time_zone="UTC"))
         .dt.total_hours())
        .alias("age_hours"),
    ])

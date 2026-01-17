from typing import Any

import polars as pl
import structlog

from src.transformation.exceptions import DataQualityError

logger = structlog.get_logger().bind(module="quality")

SchemaDefinition = dict[str, Any]

REQUIRED_COMMUNITY_SCHEMA = [
    "community_name",
    "title",
    "description",
    "subscribers",
    "is_nsfw",
    "url",
    "created_date",
    "processed_at",
]

REQUIRED_POST_SCHEMA = [
    "post_id",
    "title",
    "body",
    "url",
    "community_id",
    "community_name",
    "creator_id",
    "created_date",
    "score",
    "num_comments",
    "processed_at",
]


def validate_schema(df: pl.DataFrame, require_sources: bool = False) -> None:
    """Raises DataQualityError if required columns missing."""
    cols = set(df.columns)

    if "post_id" in cols:
        required = REQUIRED_POST_SCHEMA
    else:
        required = REQUIRED_COMMUNITY_SCHEMA

    missing_cols = [col for col in required if col not in cols]

    if require_sources and "sources" not in cols:
        missing_cols.append("sources")

    if missing_cols:
        logger.error("Schema validation failed", missing=missing_cols)
        # Identify type for clearer error message
        schema_type = "Post" if "post_id" in cols else "Community"
        raise DataQualityError(
            f"Missing required columns for {schema_type}: {missing_cols}"
        )

    logger.debug("Schema validation passed", columns=list(df.columns))


def apply_business_rules(df: pl.DataFrame) -> pl.DataFrame:
    initial_count = len(df)
    cols = df.columns

    if "community_name" in cols:
        df = df.filter(pl.col("community_name").str.strip_chars() != "")

    if "subscribers" in cols:
        df = df.filter(pl.col("subscribers") >= 0)

    if "url" in cols:
        df = df.filter(pl.col("url").is_not_null() & (pl.col("url") != ""))

    dropped = initial_count - len(df)

    if dropped > 0:
        logger.warning(
            "Rows dropped by business rules",
            initial_count=initial_count,
            final_count=len(df),
            dropped_total=dropped,
        )
    else:
        logger.debug("All rows passed business rules", row_count=len(df))

    return df


def validate_and_clean(df: pl.DataFrame, require_sources: bool = False) -> pl.DataFrame:
    validate_schema(df, require_sources=require_sources)
    return apply_business_rules(df)

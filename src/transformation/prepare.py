from typing import Any

import polars as pl
import structlog

from src.models import SourceTag, SubredditListingResponse
from src.models.reddit import SubredditData

logger = structlog.get_logger().bind(module="prepare")

SchemaDefinition = dict[str, Any]

EXTRACTED_SCHEMA: SchemaDefinition = {
    "subreddit_name": pl.String,
    "title": pl.String,
    "description": pl.String,
    "subscribers": pl.Int64,
    "is_nsfw": pl.Boolean,
    "url": pl.String,
    "created_date": pl.Float64,
    "sources": pl.List(pl.String),
}

_FIELD_MAPPING: list[tuple[str, str, type[pl.DataType]]] = [
    ("display_name", "subreddit_name", pl.String),
    ("title", "title", pl.String),
    ("public_description", "description", pl.String),
    ("subscribers", "subscribers", pl.Int64),
    ("over18", "is_nsfw", pl.Boolean),
    ("url", "url", pl.String),
    ("created_utc", "created_date", pl.Float64),
]


def _extract_to_dataframe(records: list[SubredditData]) -> pl.DataFrame:
    """Apply field mapping to convert raw API records into clean DataFrame."""
    if not records:
        schema: SchemaDefinition = {
            k: v for k, v in EXTRACTED_SCHEMA.items() if k != "sources"
        }
        return pl.DataFrame(schema=schema)

    df = pl.DataFrame(records)
    existing_cols = set(df.columns)

    selections = []
    for api_field, output_name, dtype in _FIELD_MAPPING:
        if api_field in existing_cols:
            selections.append(pl.col(api_field).cast(dtype).alias(output_name))
        else:
            selections.append(pl.lit(None).cast(dtype).alias(output_name))

    return df.select(selections)


def _extract_with_source(
    response: SubredditListingResponse, source: SourceTag
) -> pl.DataFrame:
    """Extract subreddits from a single source, adding source tag."""
    records: list[SubredditData] = [
        child["data"] for child in response["data"]["children"]
    ]

    df = _extract_to_dataframe(records)

    if df.is_empty():
        return df.with_columns(pl.lit(None).cast(pl.String).alias("source"))

    return df.with_columns(pl.lit(source).alias("source"))


def merge_sources(
    sources_data: dict[SourceTag, SubredditListingResponse]
) -> pl.DataFrame:
    """
    Merge subreddits from multiple sources, deduplicating by display_name.
    Subreddits appearing in multiple sources get all source tags in a list.
    """
    dfs: list[pl.DataFrame] = []

    for source, response in sources_data.items():
        df = _extract_with_source(response, source)
        if not df.is_empty():
            dfs.append(df)
            logger.info(
                "Extracted from source",
                source=source,
                record_count=len(df),
            )

    if not dfs:
        return pl.DataFrame(schema=EXTRACTED_SCHEMA)

    combined = pl.concat(dfs)
    logger.info("Combined sources", total_records=len(combined))
    non_key_cols = [c for c in combined.columns if c not in (
        "subreddit_name", "source")]

    merged = combined.group_by("subreddit_name").agg(
        [pl.col(c).first() for c in non_key_cols] +
        [pl.col("source").alias("sources")]
    )

    logger.info(
        "Merged sources",
        unique_subreddits=len(merged),
        duplicates_removed=len(combined) - len(merged),
    )

    return merged

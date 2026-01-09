from datetime import UTC, datetime
from typing import Any

import polars as pl
import structlog

from src.models import SourceTag, SubredditListingResponse
from src.models.reddit import SubredditData
from src.data_transformation.context import pipeline_step
from src.data_transformation.quality import validate_and_clean

logger = structlog.get_logger().bind(module="transform")

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


def _extract_to_dataframe(responses: list[SubredditListingResponse]) -> pl.DataFrame:
    records: list[SubredditData] = []

    for response in responses:
        for child in response["data"]["children"]:
            records.append(child["data"])

    if not records:
        return pl.DataFrame(schema=EXTRACTED_SCHEMA)

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
    records: list[SubredditData] = []
    for child in response["data"]["children"]:
        records.append(child["data"])

    if not records:
        schema: SchemaDefinition = {
            k: v for k, v in EXTRACTED_SCHEMA.items() if k != "sources"
        }
        schema["source"] = pl.String
        return pl.DataFrame(schema=schema)

    df = pl.DataFrame(records)
    existing_cols = set(df.columns)

    selections = []
    for api_field, output_name, dtype in _FIELD_MAPPING:
        if api_field in existing_cols:
            selections.append(pl.col(api_field).cast(dtype).alias(output_name))
        else:
            selections.append(pl.lit(None).cast(dtype).alias(output_name))

    selections.append(pl.lit(source).alias("source"))

    return df.select(selections)


def _merge_sources(
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


def _normalize_urls(df: pl.DataFrame) -> pl.DataFrame:
    """Prepend reddit.com to relative URLs. Skip URLs that are already absolute."""
    return df.with_columns(
        pl.when(pl.col("url").str.starts_with("http"))
        .then(pl.col("url"))
        .otherwise(pl.concat_str([pl.lit("https://reddit.com"), pl.col("url")]))
        .alias("url")
    )


def _convert_timestamps(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.from_epoch(pl.col("created_date")).dt.strftime(
            "%Y-%m-%d").alias("created_date")
    )


def _add_metadata(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.lit(datetime.now(UTC).isoformat()).alias("processed_at")
    )


def _log_null_stats(df: pl.DataFrame) -> pl.DataFrame:
    """Log null counts per column for data quality monitoring. Returns df unchanged."""
    total_rows = len(df)
    null_counts = {
        col: df[col].null_count()
        for col in df.columns
        if df[col].null_count() > 0
    }

    if null_counts:
        logger.warning(
            "Null values detected before filling",
            total_rows=total_rows,
            null_counts=null_counts,
            null_rate={col: round(count / total_rows, 3)
                       for col, count in null_counts.items()},
        )
    else:
        logger.debug("No null values detected")

    return df


def _fill_nulls(df: pl.DataFrame) -> pl.DataFrame:
    fills = [
        pl.col("subreddit_name").fill_null(""),
        pl.col("title").fill_null(""),
        pl.col("description").fill_null(""),
        pl.col("subscribers").fill_null(0),
        pl.col("is_nsfw").fill_null(False),
        pl.col("url").fill_null(""),
        pl.col("created_date").fill_null(""),
    ]

    if "sources" in df.columns:
        fills.append(pl.col("sources").fill_null([]))
    return df.with_columns(fills)


def _validate_data_quality(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(
        pl.col("subreddit_name").is_not_null() & (
            pl.col("subreddit_name") != "")
    )


def clean_raw_data(raw_data: list[SubredditListingResponse]) -> pl.DataFrame:
    logger.info("Starting transformation", input_records=len(raw_data))

    with pipeline_step("extract", record_count=len(raw_data)):
        df = _extract_to_dataframe(raw_data)

    if df.is_empty():
        logger.warning("No records extracted, returning empty DataFrame")
        return df

    record_count = len(df)
    logger.info("Extraction complete", extracted_records=record_count)

    with pipeline_step("normalize_urls", record_count):
        df = df.pipe(_normalize_urls)

    with pipeline_step("convert_timestamps", record_count):
        df = df.pipe(_convert_timestamps)

    with pipeline_step("add_metadata", record_count):
        df = df.pipe(_add_metadata)

    with pipeline_step("log_null_stats", record_count):
        df = df.pipe(_log_null_stats)

    with pipeline_step("fill_nulls", record_count):
        df = df.pipe(_fill_nulls)

    with pipeline_step("validate_data_quality", record_count):
        df = df.pipe(_validate_data_quality)

    final_count = len(df)
    logger.info("Transformation complete", output_records=final_count,
                dropped_records=record_count - final_count)

    return df


def clean_multi_source_data(
    sources_data: dict[SourceTag, SubredditListingResponse]
) -> pl.DataFrame:
    """
    Transform subreddits from multiple sources into a clean DataFrame.

    This function:
    1. Extracts records from each source with source tagging
    2. Merges by subreddit_name (duplicates get all source tags)
    3. Applies cleaning pipeline (URLs, timestamps, null handling)
    """
    logger.info("Starting multi-source transformation",
                sources=list(sources_data.keys()))

    with pipeline_step("merge_sources", record_count=len(sources_data)):
        df = _merge_sources(sources_data)

    if df.is_empty():
        logger.warning("No records extracted from any source")
        return df

    record_count = len(df)
    logger.info("Merge complete", unique_subreddits=record_count)

    with pipeline_step("normalize_urls", record_count):
        df = df.pipe(_normalize_urls)

    with pipeline_step("convert_timestamps", record_count):
        df = df.pipe(_convert_timestamps)

    with pipeline_step("add_metadata", record_count):
        df = df.pipe(_add_metadata)

    with pipeline_step("log_null_stats", record_count):
        df = df.pipe(_log_null_stats)

    with pipeline_step("fill_nulls", record_count):
        df = df.pipe(_fill_nulls)

    with pipeline_step("validate_and_clean", record_count):
        df = validate_and_clean(df, require_sources=True)

    final_count = len(df)
    logger.info(
        "Multi-source transformation complete",
        output_records=final_count,
        dropped_records=record_count - final_count,
        sources=list(sources_data.keys()),
    )

    return df

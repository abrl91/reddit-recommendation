from datetime import UTC, datetime

import polars as pl
import structlog

from src.models import SourceTag, SubredditListingResponse
from src.transformation.context import pipeline_step
from src.transformation.prepare import _extract_with_source, merge_sources
from src.transformation.quality import validate_and_clean

logger = structlog.get_logger().bind(module="transform")


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


def clean_source_data(
    response: SubredditListingResponse, source: SourceTag
) -> pl.DataFrame:
    """
    Transform a single source into clean Silver data.
    No merging or deduplication - just extraction and cleaning.
    """
    logger.info("Starting single-source transformation", source=source)

    with pipeline_step("extract", record_count=1):
        df = _extract_with_source(response, source)

    if df.is_empty():
        logger.warning("No records extracted from source", source=source)
        return df

    record_count = len(df)
    logger.info("Extraction complete", records=record_count)

    with pipeline_step("normalize_urls", record_count):
        df = df.pipe(_normalize_urls)

    with pipeline_step("convert_timestamps", record_count):
        df = df.pipe(_convert_timestamps)

    with pipeline_step("add_metadata", record_count):
        df = df.pipe(_add_metadata)

    with pipeline_step("log_null_stats", record_count):
        df = df.pipe(_log_null_stats)

    with pipeline_step("fill_nulls_single_source", record_count):
        df = df.with_columns([
            pl.col("subreddit_name").fill_null(""),
            pl.col("title").fill_null(""),
            pl.col("description").fill_null(""),
            pl.col("subscribers").fill_null(0),
            pl.col("is_nsfw").fill_null(False),
            pl.col("url").fill_null(""),
            pl.col("created_date").fill_null(""),
        ])

    with pipeline_step("validate_and_clean", record_count):
        df = validate_and_clean(df, require_sources=False)

    final_count = len(df)
    logger.info(
        "Single-source transformation complete",
        source=source,
        output_records=final_count,
        dropped_records=record_count - final_count,
    )

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
        df = merge_sources(sources_data)

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

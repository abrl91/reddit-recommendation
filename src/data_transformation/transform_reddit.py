from datetime import UTC, datetime

import polars as pl
import structlog

from src.models import SubredditListingResponse
from src.models.reddit import SubredditData
from src.data_transformation.context import pipeline_step

logger = structlog.get_logger().bind(module="transform")


EXTRACTED_SCHEMA = {
    "subreddit_name": pl.String,
    "title": pl.String,
    "description": pl.String,
    "subscribers": pl.Int64,
    "is_nsfw": pl.Boolean,
    "url": pl.String,
    "created_date": pl.Float64,
}

# Mapping from API field names to our schema names
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

    # Build selection: use column if exists, otherwise null literal
    selections = []
    for api_field, output_name, dtype in _FIELD_MAPPING:
        if api_field in existing_cols:
            selections.append(pl.col(api_field).cast(dtype).alias(output_name))
        else:
            selections.append(pl.lit(None).cast(dtype).alias(output_name))

    return df.select(selections)


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
            null_rate={col: round(count / total_rows, 3) for col, count in null_counts.items()},
        )
    else:
        logger.debug("No null values detected")

    return df


def _fill_nulls(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns([
        pl.col("subreddit_name").fill_null(""),
        pl.col("title").fill_null(""),
        pl.col("description").fill_null(""),
        pl.col("subscribers").fill_null(0),
        pl.col("is_nsfw").fill_null(False),
        pl.col("url").fill_null(""),
        pl.col("created_date").fill_null(""),
    ])


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

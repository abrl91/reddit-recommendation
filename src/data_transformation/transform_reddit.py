from datetime import UTC, datetime

import polars as pl

from ..models import SubredditListingResponse
from .context import pipeline_step


def _extract_to_dataframe(responses: list[SubredditListingResponse]) -> pl.DataFrame:
    records: list[dict] = []

    for response in responses:
        for child in response["data"]["children"]:
            records.append(child["data"])

    if not records:
        return pl.DataFrame()

    return pl.DataFrame(records).select([
        pl.col("display_name").alias("subreddit_name"),
        pl.col("title"),
        pl.col("public_description").alias("description"),
        pl.col("subscribers"),
        pl.col("over18").alias("is_nsfw"),
        pl.col("url"),
        pl.col("created_utc").alias("created_date"),
    ])


def _normalize_urls(df: pl.DataFrame) -> pl.DataFrame:
    """Prepend reddit.com to relative URLs."""
    return df.with_columns(
        pl.concat_str([pl.lit("https://reddit.com"), pl.col("url")]).alias("url")
    )


def _convert_timestamps(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.from_epoch(pl.col("created_date")).dt.strftime("%Y-%m-%d").alias("created_date")
    )


def _add_metadata(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.lit(datetime.now(UTC).isoformat()).alias("processed_at")
    )


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
        pl.col("subreddit_name").is_not_null() & (pl.col("subreddit_name") != "")
    )


def clean_raw_data(raw_data: list[SubredditListingResponse]) -> pl.DataFrame:
    with pipeline_step("extract", record_count=len(raw_data)):
        df = _extract_to_dataframe(raw_data)

    if df.is_empty():
        return df
    
    record_count = len(df)

    with pipeline_step("normalize_urls", record_count):
        df = df.pipe(_normalize_urls)

    with pipeline_step("convert_timestamps", record_count):
        df = df.pipe(_convert_timestamps)

    with pipeline_step("add_metadata", record_count):
        df = df.pipe(_add_metadata)

    with pipeline_step("fill_nulls", record_count):
        df = df.pipe(_fill_nulls)

    with pipeline_step("validate_data_quality", record_count):
        df = df.pipe(_validate_data_quality)

    return df

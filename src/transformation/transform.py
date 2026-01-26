from datetime import UTC, datetime

import polars as pl
import structlog

from src.config import SourceType
from src.models import RawListingResponse, RawPostResponse
from src.transformation.context import pipeline_step
from src.transformation.enrich import enrich_communities, enrich_posts
from src.transformation.prepare import extract_with_source
from src.transformation.quality import validate_and_clean
from src.transformation.utils import is_post_response

logger = structlog.get_logger().bind(module="transform")


def normalize_urls(df: pl.DataFrame) -> pl.DataFrame:
    return df


def _convert_timestamps(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("published_date")
        .str.to_datetime(time_zone="UTC", strict=False)
        .dt.strftime("%Y-%m-%d")
        .alias("created_date")
    )


def add_metadata(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.lit(datetime.now(UTC).isoformat()).alias("processed_at"))


def add_lineage(df: pl.DataFrame, source_file: str, run_id: str) -> pl.DataFrame:
    return df.with_columns([
        pl.lit(source_file).alias("source_file"),
        pl.lit(run_id).alias("run_id"),
    ])


def log_null_stats(df: pl.DataFrame) -> pl.DataFrame:
    total_rows = len(df)
    null_counts = {
        col: df[col].null_count() for col in df.columns if df[col].null_count() > 0
    }

    if null_counts:
        logger.warning(
            "Null values detected before filling",
            total_rows=total_rows,
            null_counts=null_counts,
            null_rate={
                col: round(count / total_rows, 3) for col, count in null_counts.items()
            },
        )
    else:
        logger.debug("No null values detected")

    return df


def fill_nulls(df: pl.DataFrame) -> pl.DataFrame:
    cols = df.columns
    fills = []

    # Community fields
    if "community_name" in cols:
        fills.append(pl.col("community_name").fill_null(""))
    if "title" in cols:
        fills.append(pl.col("title").fill_null(""))
    if "description" in cols:
        fills.append(pl.col("description").fill_null(""))
    if "subscribers" in cols:
        fills.append(pl.col("subscribers").fill_null(0))
    if "is_nsfw" in cols:
        fills.append(pl.col("is_nsfw").fill_null(False))
    # Note: url not filled - for posts it's semantically nullable (text posts have no url)
    # Community url is already defaulted in mapping from actor_id
    if "created_date" in cols:
        fills.append(pl.col("created_date").fill_null(""))
    if "instance" in cols:
        fills.append(pl.col("instance").fill_null("unknown"))
    # Activity metrics (community)
    if "posts_count" in cols:
        fills.append(pl.col("posts_count").fill_null(0))
    if "comments_count" in cols:
        fills.append(pl.col("comments_count").fill_null(0))
    if "users_active_week" in cols:
        fills.append(pl.col("users_active_week").fill_null(0))
    # icon/banner: keep None - they're optional display fields

    # Post fields
    # Note: body and url stay None - they're semantically nullable
    # (text posts have no url, link posts may have no body)
    if "score" in cols:
        fills.append(pl.col("score").fill_null(0))
    if "num_comments" in cols:
        fills.append(pl.col("num_comments").fill_null(0))
    # Engagement details
    if "upvotes" in cols:
        fills.append(pl.col("upvotes").fill_null(0))
    if "downvotes" in cols:
        fills.append(pl.col("downvotes").fill_null(0))
    # Display/attribution
    if "creator_name" in cols:
        fills.append(pl.col("creator_name").fill_null(""))
    # Content flags
    if "featured_community" in cols:
        fills.append(pl.col("featured_community").fill_null(False))
    if "featured_local" in cols:
        fills.append(pl.col("featured_local").fill_null(False))

    # Gold merge fields
    if "sources" in cols:
        fills.append(pl.col("sources").fill_null([]))

    return df.with_columns(fills)


def clean_source_data(
    response: RawPostResponse | RawListingResponse,
    source: SourceType,
    tag: str,
    source_file: str,
    run_id: str,
) -> pl.DataFrame:
    logger.info(
        "Starting single-source transformation",
        source=source,
        tag=tag,
        run_id=run_id,
    )

    with pipeline_step("extract", record_count=1):
        df = extract_with_source(response, source, tag)

    if df.is_empty():
        logger.warning("No records extracted from source", source=source, tag=tag)
        return df

    record_count = len(df)
    logger.info("Extraction complete", records=record_count)

    with pipeline_step("normalize_urls", record_count):
        df = df.pipe(normalize_urls)

    with pipeline_step("convert_timestamps", record_count):
        df = df.pipe(_convert_timestamps)

    with pipeline_step("add_metadata", record_count):
        df = df.pipe(add_metadata)

    with pipeline_step("enrich", record_count):
        if is_post_response(response):
            df = enrich_posts(df)
        else:
            df = enrich_communities(df)

    with pipeline_step("add_lineage", record_count):
        df = add_lineage(df, source_file, run_id)

    with pipeline_step("log_null_stats", record_count):
        df = df.pipe(log_null_stats)

    with pipeline_step("fill_nulls_single_source", record_count):
        df = df.pipe(fill_nulls)

    with pipeline_step("validate_and_clean", record_count):
        df = validate_and_clean(df, require_sources=False)

    final_count = len(df)
    logger.info(
        "Single-source transformation complete",
        source=source,
        tag=tag,
        run_id=run_id,
        output_records=final_count,
        dropped_records=record_count - final_count,
    )

    return df

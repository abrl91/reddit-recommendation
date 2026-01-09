import polars as pl
import structlog

from src.models import SourceTag
from src.transformation.context import pipeline_step
from src.transformation.quality import validate_and_clean

logger = structlog.get_logger().bind(module="gold")


def merge_silver_sources(silver_data: dict[SourceTag, pl.DataFrame]) -> pl.DataFrame:
    """
    Merge all Silver sources into Gold, deduplicating by subreddit_name.
    Subreddits appearing in multiple sources get all source tags in a list.
    """
    if not silver_data:
        logger.warning("No silver sources provided for Gold merge")
        return pl.DataFrame()

    logger.info(
        "Starting Gold merge",
        sources=list(silver_data.keys()),
        source_counts={s.value: len(df) for s, df in silver_data.items()},
    )

    dfs: list[pl.DataFrame] = []
    for source, df in silver_data.items():
        if df.is_empty():
            logger.warning("Empty DataFrame for source", source=source)
            continue
        dfs.append(df)

    if not dfs:
        logger.warning("All silver sources were empty")
        return pl.DataFrame()

    with pipeline_step("concatenate", record_count=len(dfs)):
        combined = pl.concat(dfs)

    total_records = len(combined)
    logger.info("Combined silver sources", total_records=total_records)

    with pipeline_step("deduplicate_and_aggregate", record_count=total_records):
        non_key_cols = [
            c for c in combined.columns if c not in ("subreddit_name", "source")
        ]

        merged = combined.group_by("subreddit_name").agg(
            [pl.col(c).first() for c in non_key_cols]
            + [pl.col("source").alias("sources")]
        )

    unique_count = len(merged)
    logger.info(
        "Gold merge complete",
        unique_subreddits=unique_count,
        duplicates_merged=total_records - unique_count,
    )

    with pipeline_step("validate_gold", record_count=unique_count):
        merged = validate_and_clean(merged, require_sources=True)

    final_count = len(merged)
    logger.info(
        "Gold validation complete",
        output_records=final_count,
        dropped_records=unique_count - final_count,
    )

    return merged

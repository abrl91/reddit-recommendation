import polars as pl
import structlog

from src.transformation.context import pipeline_step
from src.transformation.quality import validate_and_clean

logger = structlog.get_logger().bind(module="gold")


def merge_silver_sources(silver_data: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Deduplicates by community_name, aggregates source tags into list."""
    if not silver_data:
        logger.warning("No silver sources provided for Gold merge")
        return pl.DataFrame()

    logger.info(
        "Starting Gold merge",
        tags=list(silver_data.keys()),
        tag_counts={tag: len(df) for tag, df in silver_data.items()},
    )

    dfs: list[pl.DataFrame] = []
    for tag, df in silver_data.items():
        if df.is_empty():
            logger.warning("Empty DataFrame for tag", tag=tag)
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
            c for c in combined.columns if c not in ("community_name", "source")
        ]

        merged = combined.group_by("community_name").agg(
            [pl.col(c).first() for c in non_key_cols]
            + [pl.col("source").alias("sources")]
        )

    unique_count = len(merged)
    logger.info(
        "Gold merge complete",
        unique_communities=unique_count,
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

from typing import Any

import polars as pl
import structlog

from src.transformation.exceptions import DataQualityError

logger = structlog.get_logger().bind(module="quality")

SchemaDefinition = dict[str, Any]

REQUIRED_SCHEMA: SchemaDefinition = {
    "subreddit_name": pl.String,
    "title": pl.String,
    "description": pl.String,
    "subscribers": pl.Int64,
    "is_nsfw": pl.Boolean,
    "url": pl.String,
    "created_date": pl.String,
    "processed_at": pl.String,
}


def validate_schema(df: pl.DataFrame, require_sources: bool = False) -> None:
    """
    Validate DataFrame has required columns with correct types.
    Raises DataQualityError if schema is invalid.

    When require_sources=True, expects 'sources' column (list) for Gold data.
    When require_sources=False, expects 'source' column (string) for Silver data.
    """
    required: SchemaDefinition = dict(REQUIRED_SCHEMA)
    if require_sources:
        required["sources"] = pl.List(pl.String)
    else:
        required["source"] = pl.String

    missing_cols = set(required.keys()) - set(df.columns)
    if missing_cols:
        raise DataQualityError(f"Missing required columns: {missing_cols}")

    for col_name, expected_type in required.items():
        actual_type = df.schema[col_name]
        # Compare base type (ignoring nullability)
        if actual_type.base_type() != expected_type.base_type():
            raise DataQualityError(
                f"Column '{col_name}' has type {actual_type}, expected {expected_type}"
            )

    logger.debug("Schema validation passed", columns=list(df.columns))


def apply_business_rules(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply business rules, filtering out invalid rows.
    Returns cleaned DataFrame and logs quality metrics.
    """
    initial_count = len(df)

    df = df.filter(
        pl.col("subreddit_name").is_not_null() & (
            pl.col("subreddit_name") != "")
    )
    after_name_check = len(df)

    df = df.filter(pl.col("subscribers").is_null()
                   | (pl.col("subscribers") >= 0))
    after_subscriber_check = len(df)
    df = df.filter(pl.col("url").is_not_null() & (pl.col("url") != ""))
    after_url_check = len(df)

    dropped = initial_count - len(df)
    if dropped > 0:
        logger.warning(
            "Rows dropped by business rules",
            initial_count=initial_count,
            final_count=len(df),
            dropped_total=dropped,
            dropped_empty_name=initial_count - after_name_check,
            dropped_negative_subscribers=after_name_check - after_subscriber_check,
            dropped_empty_url=after_subscriber_check - after_url_check,
        )
    else:
        logger.debug("All rows passed business rules", row_count=len(df))

    return df


def validate_and_clean(df: pl.DataFrame, require_sources: bool = False) -> pl.DataFrame:
    validate_schema(df, require_sources=require_sources)
    return apply_business_rules(df)

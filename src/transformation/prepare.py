from typing import Any

import polars as pl

from src.models import SourceTag, SubredditListingResponse
from src.models.reddit import SubredditData

SchemaDefinition = dict[str, Any]

EXTRACTED_SCHEMA: SchemaDefinition = {
    "subreddit_name": pl.String,
    "title": pl.String,
    "description": pl.String,
    "subscribers": pl.Int64,
    "is_nsfw": pl.Boolean,
    "url": pl.String,
    "created_date": pl.Float64,
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


def extract_to_dataframe(records: list[SubredditData]) -> pl.DataFrame:
    """Apply field mapping to convert raw API records into clean DataFrame."""
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


def extract_with_source(
    response: SubredditListingResponse, source: SourceTag
) -> pl.DataFrame:
    """Extract subreddits from a single source, adding source tag."""
    records: list[SubredditData] = [
        child["data"] for child in response["data"]["children"]
    ]

    df = extract_to_dataframe(records)

    if df.is_empty():
        return df.with_columns(pl.lit(None).cast(pl.String).alias("source"))

    return df.with_columns(pl.lit(source).alias("source"))

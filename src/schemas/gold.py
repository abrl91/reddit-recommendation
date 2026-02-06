import polars as pl

from src.schemas.silver import (
    SILVER_COMMUNITY_SCHEMA,
    SILVER_POST_SCHEMA,
    SchemaDefinition,
)

GOLD_COMMUNITY_SCHEMA: SchemaDefinition = {
    **{k: v for k, v in SILVER_COMMUNITY_SCHEMA.items() if k != "source"},
    "sources": pl.List(pl.String),
}

GOLD_POST_SCHEMA: SchemaDefinition = {
    **{k: v for k, v in SILVER_POST_SCHEMA.items() if k != "source"},
    "sources": pl.List(pl.String),
}

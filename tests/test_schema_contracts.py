import polars as pl

from src.schemas import (
    GOLD_COMMUNITY_SCHEMA,
    GOLD_POST_SCHEMA,
    SILVER_COMMUNITY_SCHEMA,
    SILVER_POST_SCHEMA,
)
from src.transformation.prepare import COMMUNITY_SCHEMA, POST_SCHEMA
from src.transformation.quality import REQUIRED_COMMUNITY_SCHEMA, REQUIRED_POST_SCHEMA


class TestSilverSchemaContracts:
    """Silver schema must be a superset of base extraction schemas."""

    def test_silver_community_includes_all_base_fields(self) -> None:
        for field in COMMUNITY_SCHEMA:
            assert field in SILVER_COMMUNITY_SCHEMA, f"Missing base field: {field}"

    def test_silver_post_includes_all_base_fields(self) -> None:
        for field in POST_SCHEMA:
            assert field in SILVER_POST_SCHEMA, f"Missing base field: {field}"

    def test_silver_community_has_metadata_fields(self) -> None:
        for field in ["source", "created_date", "processed_at"]:
            assert field in SILVER_COMMUNITY_SCHEMA, f"Missing metadata: {field}"

    def test_silver_post_has_metadata_fields(self) -> None:
        for field in ["source", "created_date", "processed_at"]:
            assert field in SILVER_POST_SCHEMA, f"Missing metadata: {field}"

    def test_silver_community_has_enrichment_fields(self) -> None:
        enrichment = ["description_length", "is_active_community", "age_hours"]
        for field in enrichment:
            assert field in SILVER_COMMUNITY_SCHEMA, f"Missing enrichment: {field}"

    def test_silver_post_has_enrichment_fields(self) -> None:
        enrichment = [
            "engagement_ratio",
            "comment_density",
            "content_type",
            "body_length",
            "age_hours",
        ]
        for field in enrichment:
            assert field in SILVER_POST_SCHEMA, f"Missing enrichment: {field}"

    def test_silver_community_has_lineage_fields(self) -> None:
        for field in ["source_file", "run_id"]:
            assert field in SILVER_COMMUNITY_SCHEMA, f"Missing lineage: {field}"

    def test_silver_post_has_lineage_fields(self) -> None:
        for field in ["source_file", "run_id"]:
            assert field in SILVER_POST_SCHEMA, f"Missing lineage: {field}"

    def test_silver_satisfies_quality_requirements_community(self) -> None:
        for field in REQUIRED_COMMUNITY_SCHEMA:
            assert field in SILVER_COMMUNITY_SCHEMA, (
                f"Quality requires '{field}' but silver schema doesn't include it"
            )

    def test_silver_satisfies_quality_requirements_post(self) -> None:
        for field in REQUIRED_POST_SCHEMA:
            assert field in SILVER_POST_SCHEMA, (
                f"Quality requires '{field}' but silver schema doesn't include it"
            )


class TestGoldSchemaContracts:
    """Gold replaces 'source' with 'sources' list."""

    def test_gold_community_has_sources_not_source(self) -> None:
        assert "sources" in GOLD_COMMUNITY_SCHEMA
        assert "source" not in GOLD_COMMUNITY_SCHEMA
        assert GOLD_COMMUNITY_SCHEMA["sources"] == pl.List(pl.String)

    def test_gold_post_has_sources_not_source(self) -> None:
        assert "sources" in GOLD_POST_SCHEMA
        assert "source" not in GOLD_POST_SCHEMA
        assert GOLD_POST_SCHEMA["sources"] == pl.List(pl.String)

    def test_gold_community_preserves_all_non_source_fields(self) -> None:
        silver_non_source = {k for k in SILVER_COMMUNITY_SCHEMA if k != "source"}
        gold_non_sources = {k for k in GOLD_COMMUNITY_SCHEMA if k != "sources"}
        assert silver_non_source == gold_non_sources

    def test_gold_post_preserves_all_non_source_fields(self) -> None:
        silver_non_source = {k for k in SILVER_POST_SCHEMA if k != "source"}
        gold_non_sources = {k for k in GOLD_POST_SCHEMA if k != "sources"}
        assert silver_non_source == gold_non_sources


class TestSchemaTypeConsistency:
    """Base types in prepare.py match silver schema types."""

    def test_community_base_types_match(self) -> None:
        for field, dtype in COMMUNITY_SCHEMA.items():
            assert SILVER_COMMUNITY_SCHEMA[field] == dtype, (
                f"{field}: prepare={dtype} != silver={SILVER_COMMUNITY_SCHEMA[field]}"
            )

    def test_post_base_types_match(self) -> None:
        for field, dtype in POST_SCHEMA.items():
            assert SILVER_POST_SCHEMA[field] == dtype, (
                f"{field}: prepare={dtype} != silver={SILVER_POST_SCHEMA[field]}"
            )

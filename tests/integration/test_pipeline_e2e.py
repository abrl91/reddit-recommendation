import polars as pl
import pytest
from mypy_boto3_s3 import S3Client

from src import RunContext, create_bronze_source, create_gold, create_silver_source
from src.schemas import SILVER_COMMUNITY_SCHEMA


MOCK_COMMUNITY_RESPONSE = {
    "communities": [
        {
            "community": {
                "id": 1,
                "name": "python",
                "title": "Python Programming",
                "description": "News about the Python language",
                "nsfw": False,
                "actor_id": "https://lemmy.world/c/python",
                "published": "2023-01-01T12:00:00Z",
            },
            "counts": {
                "subscribers": 50000,
                "posts": 1200,
                "comments": 8500,
                "users_active_week": 120,
            },
        },
        {
            "community": {
                "id": 2,
                "name": "rust",
                "title": "Rust Language",
                "description": "All things Rust",
                "nsfw": False,
                "actor_id": "https://lemmy.world/c/rust",
                "published": "2023-03-15T08:00:00Z",
            },
            "counts": {
                "subscribers": 30000,
                "posts": 800,
                "comments": 5000,
                "users_active_week": 80,
            },
        },
    ]
}


@pytest.mark.integration
class TestBronzeToSilver:
    """Test bronze → silver pipeline against real S3 (LocalStack)."""

    def test_communities_bronze_to_silver(
        self, clean_buckets: S3Client, mocker: object
    ) -> None:
        """Bronze ingest → Silver transform produces valid community data."""
        mocker.patch(  # type: ignore[union-attr]
            "src.ingestion.fetch_lemmy.make_request",
            return_value=MOCK_COMMUNITY_RESPONSE,
        )

        run_ctx = RunContext.create()
        create_bronze_source("communities", "hot", run_ctx)
        create_silver_source("communities", "hot", run_ctx)

        from src.storage import read_silver

        silver_df = read_silver("communities", "hot")
        assert silver_df is not None

        # Shape: 2 communities from mock, all schema columns present
        assert len(silver_df) == 2
        assert set(silver_df.columns) == set(SILVER_COMMUNITY_SCHEMA.keys())

        # Data correctness: values match mock input
        names = sorted(silver_df["community_name"].to_list())
        assert names == ["python", "rust"]
        assert (
            silver_df.filter(pl.col("community_name") == "python")["subscribers"][0]
            == 50000
        )
        assert (
            silver_df.filter(pl.col("community_name") == "python")["title"][0]
            == "Python Programming"
        )
        assert silver_df["source"].to_list() == ["communities_hot"] * 2

        # Enrichment: derived columns have reasonable values
        assert all(v > 0 for v in silver_df["description_length"].to_list())
        assert all(v > 0 for v in silver_df["age_hours"].to_list())
        # Both communities have users_active_week > threshold (10), so both active
        assert all(silver_df["is_active_community"].to_list())

        # Lineage: traceable back to this run
        assert all(rid == run_ctx.run_id for rid in silver_df["run_id"].to_list())
        assert all(sf != "" for sf in silver_df["source_file"].to_list())


@pytest.mark.integration
class TestFullPipelineWithDedup:
    """Test full bronze → silver → gold with deduplication."""

    def test_gold_deduplicates_across_tags(
        self, clean_buckets: S3Client, mocker: object
    ) -> None:
        """Same community from two tags → gold has one row with both sources."""
        mocker.patch(  # type: ignore[union-attr]
            "src.ingestion.fetch_lemmy.make_request",
            return_value=MOCK_COMMUNITY_RESPONSE,
        )

        run_ctx = RunContext.create()

        # Ingest same data through two different tags
        for tag in ["hot", "new"]:
            create_bronze_source("communities", tag, run_ctx)
            create_silver_source("communities", tag, run_ctx)

        create_gold("communities", run_ctx)

        # Read gold and verify deduplication
        # Gold uses day-level partitioning (no hour)
        from src.config import get_gold_location, get_partition_path
        from src.storage.read import _get_polars_storage_options

        bucket, prefix = get_gold_location("communities")
        partition = get_partition_path(prefix, include_hour=False)
        s3_path = f"s3://{bucket}/{partition}/data.parquet"
        gold_df = pl.read_parquet(
            s3_path, storage_options=_get_polars_storage_options()
        )

        # 2 unique communities despite ingesting from 2 tags
        assert len(gold_df) == 2

        # Each community should have both source tags
        for sources in gold_df["sources"].to_list():
            assert "communities_hot" in sources
            assert "communities_new" in sources

        # Gold should have "sources" (list) not "source" (string)
        assert "sources" in gold_df.columns
        assert "source" not in gold_df.columns

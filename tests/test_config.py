from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.config import (
    get_bronze_location,
    get_gold_location,
    get_gold_tags,
    get_partition_path,
    get_s3_bucket,
    get_silver_location,
    get_stream_config,
)


class TestGetPartitionPath:
    def test_formats_single_digit_month_and_day(self) -> None:
        """Single-digit months/days should be zero-padded."""
        dt = datetime(2025, 1, 5, tzinfo=UTC)
        result = get_partition_path("prefix", dt)
        assert result == "prefix/year=2025/month=01/day=05"

    def test_formats_double_digit_month_and_day(self) -> None:
        """Double-digit months/days should not have extra padding."""
        dt = datetime(2025, 12, 25, tzinfo=UTC)
        result = get_partition_path("prefix", dt)
        assert result == "prefix/year=2025/month=12/day=25"

    def test_with_custom_prefix(self) -> None:
        """Prefix should be included in the path."""
        dt = datetime(2025, 6, 15, tzinfo=UTC)
        result = get_partition_path("posts/hot", dt)
        assert result == "posts/hot/year=2025/month=06/day=15"

    def test_defaults_to_current_time_when_no_date(self) -> None:
        """When date is None, should use current UTC time."""
        with patch("src.config.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 3, 10, tzinfo=UTC)
            result = get_partition_path("prefix", None)
            assert result == "prefix/year=2025/month=03/day=10"
            mock_datetime.now.assert_called_once_with(UTC)

    def test_with_hour_included(self) -> None:
        """When include_hour=True, should add hour partition."""
        dt = datetime(2025, 6, 15, 14, tzinfo=UTC)
        result = get_partition_path("prefix", dt, include_hour=True)
        assert result == "prefix/year=2025/month=06/day=15/hour=14"


class TestGetStreamConfig:
    def test_returns_config_for_valid_stream(self) -> None:
        """Valid source/tag should return stream config."""
        config = get_stream_config("posts", "hot")
        assert config["sort"] == "Hot"
        assert config["limit"] == 50

    def test_returns_config_for_communities(self) -> None:
        """Communities stream should have different limit."""
        config = get_stream_config("communities", "hot")
        assert config["sort"] == "Hot"
        assert config["limit"] == 25

    def test_raises_key_error_for_invalid_tag(self) -> None:
        """Invalid tag should raise KeyError."""
        with pytest.raises(KeyError):
            get_stream_config("posts", "nonexistent_tag")


class TestGetBronzeLocation:
    def test_returns_bucket_and_prefix(self) -> None:
        """Should return (bucket, prefix) tuple for bronze layer."""
        bucket, prefix = get_bronze_location("posts", "hot")
        assert "bronze" in bucket
        assert prefix == "posts/hot"


class TestGetSilverLocation:
    def test_returns_bucket_and_prefix(self) -> None:
        """Should return (bucket, prefix) tuple for silver layer."""
        bucket, prefix = get_silver_location("communities", "new")
        assert "silver" in bucket
        assert prefix == "communities/new"


class TestGetGoldLocation:
    def test_returns_bucket_and_source_prefix(self) -> None:
        """Gold location should use source as prefix (no tag)."""
        bucket, prefix = get_gold_location("posts")
        assert "gold" in bucket
        assert prefix == "posts"

    def test_communities_gold_location(self) -> None:
        """Communities gold should use 'communities' prefix."""
        bucket, prefix = get_gold_location("communities")
        assert prefix == "communities"


class TestGetGoldTags:
    def test_returns_configured_tags_for_source(self) -> None:
        """Should return list of tags configured for gold merge."""
        tags = get_gold_tags("communities")
        assert "hot" in tags
        assert "new" in tags
        assert isinstance(tags, list)

    def test_posts_has_more_tags(self) -> None:
        """Posts should have more tags than communities."""
        posts_tags = get_gold_tags("posts")
        community_tags = get_gold_tags("communities")
        assert len(posts_tags) > len(community_tags)


class TestGetS3Bucket:
    @pytest.mark.parametrize(
        "layer,expected_contains",
        [
            ("bronze", "bronze"),
            ("silver", "silver"),
            ("gold", "gold"),
        ],
    )
    def test_valid_layers_return_bucket(
        self, layer: str, expected_contains: str
    ) -> None:
        """Valid layer names should return bucket containing the layer name."""
        result = get_s3_bucket(layer)  # type: ignore[arg-type]
        assert expected_contains in result

    def test_invalid_layer_raises_key_error(self) -> None:
        """Invalid layer name should raise KeyError."""
        with pytest.raises(KeyError):
            get_s3_bucket("invalid_layer")  # type: ignore[arg-type]

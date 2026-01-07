from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.config import get_data_path, get_partition_path, get_s3_bucket


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
        result = get_partition_path("my_data/subreddits", dt)
        assert result == "my_data/subreddits/year=2025/month=06/day=15"

    def test_defaults_to_current_time_when_no_date(self) -> None:
        """When date is None, should use current UTC time."""
        with patch("src.config.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 3, 10, tzinfo=UTC)
            result = get_partition_path("prefix", None)
            assert result == "prefix/year=2025/month=03/day=10"
            mock_datetime.now.assert_called_once_with(UTC)


class TestGetDataPath:
    def test_returns_bucket_and_prefix_for_valid_key(self) -> None:
        """Valid data_type_key should return (bucket, prefix) tuple."""
        bucket, prefix = get_data_path("raw_popular_subreddits")
        assert bucket == "reddit-data-bronze-d271225"
        assert prefix == "popular_subreddits"

    def test_raises_key_error_for_invalid_key(self) -> None:
        """Invalid data_type_key should raise KeyError."""
        with pytest.raises(KeyError):
            get_data_path("nonexistent_data_type")


class TestGetS3Bucket:
    @pytest.mark.parametrize("layer,expected_contains", [
        ("bronze", "bronze"),
        ("silver", "silver"),
    ])
    def test_valid_layers_return_bucket(self, layer: str, expected_contains: str) -> None:
        """Valid layer names should return bucket containing the layer name."""
        result = get_s3_bucket(layer)  # type: ignore[arg-type]
        assert expected_contains in result

    def test_invalid_layer_raises_key_error(self) -> None:
        """Invalid layer name should raise KeyError."""
        with pytest.raises(KeyError):
            get_s3_bucket("invalid_layer")  # type: ignore[arg-type]

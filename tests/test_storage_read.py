import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.storage.exceptions import StorageError
from src.storage.read_from_dest import read_json_from_s3, read_parquet_from_s3


class TestReadJsonFromS3:
    def test_returns_all_json_files_from_partition(self, mocker: Any) -> None:
        """Should return combined data from all JSON files in partition."""
        mock_client = MagicMock()

        # Mock paginator to return 2 JSON files
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "prefix/year=2025/month=01/day=07/file1.json"},
                    {"Key": "prefix/year=2025/month=01/day=07/file2.json"},
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        # Mock get_object for each file
        response1 = {"kind": "Listing", "data": {"children": [{"data": {"name": "sub1"}}]}}
        response2 = {"kind": "Listing", "data": {"children": [{"data": {"name": "sub2"}}]}}

        mock_client.get_object.side_effect = [
            {"Body": MagicMock(read=MagicMock(return_value=json.dumps(response1).encode()))},
            {"Body": MagicMock(read=MagicMock(return_value=json.dumps(response2).encode()))},
        ]

        mocker.patch("boto3.client", return_value=mock_client)

        with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
            mock_path.return_value = "prefix/year=2025/month=01/day=07"
            result = read_json_from_s3("raw_subreddits_popular")

        assert len(result) == 2
        assert result[0]["data"]["children"][0]["data"]["name"] == "sub1"
        assert result[1]["data"]["children"][0]["data"]["name"] == "sub2"

    def test_empty_partition_returns_empty_list(self, mocker: Any) -> None:
        """Partition with no files should return empty list."""
        mock_client = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]  # No "Contents" key
        mock_client.get_paginator.return_value = mock_paginator

        mocker.patch("boto3.client", return_value=mock_client)

        with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
            mock_path.return_value = "prefix/year=2025/month=01/day=07"
            result = read_json_from_s3("raw_subreddits_popular")

        assert result == []

    def test_corrupted_file_continues_with_others(self, mocker: Any) -> None:
        """Corrupted JSON file should be logged and skipped, others returned."""
        mock_client = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "prefix/file1.json"},  # Valid
                    {"Key": "prefix/file2.json"},  # Corrupted
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        valid_response = {"kind": "Listing", "data": {"children": []}}

        mock_client.get_object.side_effect = [
            {"Body": MagicMock(read=MagicMock(return_value=json.dumps(valid_response).encode()))},
            {"Body": MagicMock(read=MagicMock(return_value=b"not valid json{{{"))},
        ]

        mocker.patch("boto3.client", return_value=mock_client)

        with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
            mock_path.return_value = "prefix"
            result = read_json_from_s3("raw_subreddits_popular")

        # Should return only the valid file
        assert len(result) == 1
        assert result[0]["kind"] == "Listing"

    def test_bucket_not_found_raises_storage_error(self, mocker: Any) -> None:
        """NoSuchBucket error should raise StorageError."""
        mock_client = MagicMock()

        # Create a proper NoSuchBucket exception
        mock_client.exceptions.NoSuchBucket = type("NoSuchBucket", (Exception,), {})

        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = mock_client.exceptions.NoSuchBucket()
        mock_client.get_paginator.return_value = mock_paginator

        mocker.patch("boto3.client", return_value=mock_client)

        with pytest.raises(StorageError) as exc_info:
            with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
                mock_path.return_value = "prefix"
                read_json_from_s3("raw_subreddits_popular")

        assert "does not exist" in str(exc_info.value)

    def test_custom_date_uses_correct_partition(self, mocker: Any) -> None:
        """Custom date parameter should be passed to partition path generator."""
        mock_client = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        mock_client.get_paginator.return_value = mock_paginator

        mocker.patch("boto3.client", return_value=mock_client)

        custom_date = datetime(2024, 6, 15, tzinfo=UTC)

        with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
            mock_path.return_value = "prefix/year=2024/month=06/day=15"
            read_json_from_s3("raw_subreddits_popular", date=custom_date)

        mock_path.assert_called_once()
        call_args = mock_path.call_args
        assert call_args[1]["date"] == custom_date


class TestReadParquetFromS3:
    def test_reads_from_correct_s3_path(self, mocker: Any) -> None:
        """Should construct correct S3 glob path for partition."""
        mock_df = pl.DataFrame({"col1": [1, 2, 3]})
        mock_read = mocker.patch("polars.read_parquet", return_value=mock_df)

        with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
            mock_path.return_value = "popular_subreddits/year=2025/month=01/day=07"
            result = read_parquet_from_s3("cleaned_subreddits_popular")

        mock_read.assert_called_once()
        s3_url = mock_read.call_args[0][0]

        assert "s3://" in s3_url
        assert "year=2025" in s3_url
        assert s3_url.endswith("/*.parquet")
        assert len(result) == 3

    def test_read_error_raises_storage_error(self, mocker: Any) -> None:
        """Parquet read errors should be wrapped in StorageError."""
        mocker.patch("polars.read_parquet", side_effect=Exception("File not found"))

        with pytest.raises(StorageError) as exc_info:
            with patch("src.storage.read_from_dest.get_partition_path") as mock_path:
                mock_path.return_value = "prefix/year=2025/month=01/day=07"
                read_parquet_from_s3("cleaned_subreddits_popular")

        assert "Failed to read parquet" in str(exc_info.value)

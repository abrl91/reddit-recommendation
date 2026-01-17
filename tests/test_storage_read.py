import json
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.storage.exceptions import StorageError
from src.storage.read import read_bronze, read_silver


class TestReadBronze:
    def test_returns_data_from_json_file(self, mocker: Any) -> None:
        """Should return parsed JSON data from S3 partition."""
        mock_client = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "posts/hot/year=2025/month=01/day=07/data.json"}]}
        ]
        mock_client.get_paginator.return_value = mock_paginator

        response = {"posts": [{"post": {"id": 1, "name": "Test"}}]}
        mock_client.get_object.return_value = {
            "Body": MagicMock(
                read=MagicMock(return_value=json.dumps(response).encode())
            )
        }

        mocker.patch("boto3.client", return_value=mock_client)

        with patch("src.storage.read.get_partition_path") as mock_path:
            mock_path.return_value = "posts/hot/year=2025/month=01/day=07"
            result = read_bronze("posts", "hot")

        assert result is not None
        assert result["posts"][0]["post"]["name"] == "Test"

    def test_returns_none_when_no_data(self, mocker: Any) -> None:
        """Should return None when partition has no files."""
        mock_client = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]  # No "Contents"
        mock_client.get_paginator.return_value = mock_paginator

        mocker.patch("boto3.client", return_value=mock_client)

        with patch("src.storage.read.get_partition_path") as mock_path:
            mock_path.return_value = "posts/hot/year=2025/month=01/day=07"
            result = read_bronze("posts", "hot")

        assert result is None

    def test_bucket_not_found_raises_storage_error(self, mocker: Any) -> None:
        """NoSuchBucket error should raise StorageError."""
        mock_client = MagicMock()
        mock_client.exceptions.NoSuchBucket = type("NoSuchBucket", (Exception,), {})

        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = mock_client.exceptions.NoSuchBucket()
        mock_client.get_paginator.return_value = mock_paginator

        mocker.patch("boto3.client", return_value=mock_client)

        with pytest.raises(StorageError) as exc_info:
            with patch("src.storage.read.get_partition_path") as mock_path:
                mock_path.return_value = "posts/hot/year=2025/month=01/day=07"
                read_bronze("posts", "hot")

        assert "does not exist" in str(exc_info.value)


class TestReadSilver:
    def test_reads_parquet_from_correct_path(self, mocker: Any) -> None:
        """Should construct correct S3 glob path for partition."""
        mock_df = pl.DataFrame({"col1": [1, 2, 3]})
        mock_read = mocker.patch("polars.read_parquet", return_value=mock_df)

        with patch("src.storage.read.get_partition_path") as mock_path:
            mock_path.return_value = "communities/hot/year=2025/month=01/day=07"
            result = read_silver("communities", "hot")

        mock_read.assert_called_once()
        s3_url = mock_read.call_args[0][0]

        assert "s3://" in s3_url
        assert "communities/hot" in s3_url
        assert result is not None
        assert len(result) == 3

    def test_returns_none_on_read_error(self, mocker: Any) -> None:
        """Parquet read errors should return None (not raise)."""
        mocker.patch("polars.read_parquet", side_effect=Exception("File not found"))

        with patch("src.storage.read.get_partition_path") as mock_path:
            mock_path.return_value = "posts/hot/year=2025/month=01/day=07"
            result = read_silver("posts", "hot")

        assert result is None

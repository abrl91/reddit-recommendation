import json
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from botocore.exceptions import ClientError

from src.storage.exceptions import StorageError
from src.storage.write import save_bronze, save_gold, save_silver


class TestSaveBronze:
    def test_uploads_to_correct_partition_path(self, mocker: Any) -> None:
        """Should upload to Hive-style partition path."""
        mock_client = MagicMock()
        mocker.patch("boto3.client", return_value=mock_client)

        data = {"posts": [{"post": {"id": 1}}]}

        with patch("src.storage.write.get_partition_path") as mock_path:
            mock_path.return_value = "posts/hot/year=2025/month=01/day=07/hour=14"
            save_bronze(data, "posts", "hot", include_hour=True)  # type: ignore[arg-type]

        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]

        assert "year=2025" in call_kwargs["Key"]
        assert call_kwargs["Key"].endswith("/data.json")

    def test_serializes_data_as_json(self, mocker: Any) -> None:
        """Data should be JSON-encoded in request body."""
        mock_client = MagicMock()
        mocker.patch("boto3.client", return_value=mock_client)

        data = {"communities": [{"community": {"name": "test"}}]}

        with patch("src.storage.write.get_partition_path") as mock_path:
            mock_path.return_value = "communities/hot/year=2025/month=01/day=07"
            save_bronze(data, "communities", "hot")  # type: ignore[arg-type]

        call_kwargs = mock_client.put_object.call_args[1]
        body = call_kwargs["Body"]

        assert json.loads(body) == data

    def test_client_error_raises_storage_error(self, mocker: Any) -> None:
        """S3 ClientError should be wrapped in StorageError."""
        mock_client = MagicMock()
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        mocker.patch("boto3.client", return_value=mock_client)

        with pytest.raises(StorageError) as exc_info:
            with patch("src.storage.write.get_partition_path") as mock_path:
                mock_path.return_value = "posts/hot/year=2025/month=01/day=07"
                save_bronze({"posts": []}, "posts", "hot")  # type: ignore[arg-type]

        assert "Failed to save bronze" in str(exc_info.value)


class TestSaveSilver:
    def test_saves_dataframe_to_correct_path(self, mocker: Any) -> None:
        """DataFrame should be saved to Hive-style partition path."""
        mock_write = mocker.patch.object(pl.DataFrame, "write_parquet")

        df = pl.DataFrame({"col1": [1, 2, 3]})

        with patch("src.storage.write.get_partition_path") as mock_path:
            mock_path.return_value = "posts/hot/year=2025/month=01/day=07/hour=14"
            save_silver(df, "posts", "hot", include_hour=True)

        mock_write.assert_called_once()
        s3_path = mock_write.call_args[0][0]

        assert "s3://" in s3_path
        assert "year=2025" in s3_path
        assert s3_path.endswith("/data.parquet")

    def test_write_error_raises_storage_error(self, mocker: Any) -> None:
        """Parquet write errors should be wrapped in StorageError."""
        mocker.patch.object(
            pl.DataFrame,
            "write_parquet",
            side_effect=Exception("S3 write failed"),
        )

        df = pl.DataFrame({"col1": [1, 2, 3]})

        with pytest.raises(StorageError) as exc_info:
            with patch("src.storage.write.get_partition_path") as mock_path:
                mock_path.return_value = "posts/hot/year=2025/month=01/day=07"
                save_silver(df, "posts", "hot")

        assert "Failed to save silver" in str(exc_info.value)


class TestSaveGold:
    def test_saves_to_source_prefix_without_tag(self, mocker: Any) -> None:
        """Gold should be saved using source as prefix (no tag)."""
        mock_write = mocker.patch.object(pl.DataFrame, "write_parquet")

        df = pl.DataFrame({"community_name": ["python"], "sources": [["hot", "new"]]})

        with patch("src.storage.write.get_partition_path") as mock_path:
            mock_path.return_value = "communities/year=2025/month=01/day=07"
            save_gold(df, "communities")

        mock_write.assert_called_once()
        s3_path = mock_write.call_args[0][0]

        assert "communities" in s3_path
        assert "hot" not in s3_path  # No tag in gold path

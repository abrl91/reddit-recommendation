import json
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from botocore.exceptions import ClientError

from src.storage.exceptions import StorageError
from src.storage.write_to_dest import save_json_to_s3, save_parquet_to_s3


class TestSaveJsonToS3:
    def test_uploads_to_correct_partition_path(self, mocker: Any) -> None:
        """Should upload to Hive-style partition path."""
        mock_client = MagicMock()
        mocker.patch("boto3.client", return_value=mock_client)

        data = {"kind": "Listing", "data": {"children": []}}

        with patch("src.storage.write_to_dest.get_partition_path") as mock_path:
            mock_path.return_value = "popular_subreddits/year=2025/month=01/day=07"
            save_json_to_s3(data, "raw_subreddits_popular")

        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]

        assert "year=2025" in call_kwargs["Key"]
        assert call_kwargs["Key"].endswith("/data.json")

    def test_serializes_data_as_json(self, mocker: Any) -> None:
        """Data should be JSON-encoded in request body."""
        mock_client = MagicMock()
        mocker.patch("boto3.client", return_value=mock_client)

        data = {"kind": "Listing", "data": {"children": []}}

        with patch("src.storage.write_to_dest.get_partition_path") as mock_path:
            mock_path.return_value = "prefix/year=2025/month=01/day=07"
            save_json_to_s3(data, "raw_subreddits_popular")

        call_kwargs = mock_client.put_object.call_args[1]
        body = call_kwargs["Body"]

        # Should be valid JSON that matches input
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
            with patch("src.storage.write_to_dest.get_partition_path") as mock_path:
                mock_path.return_value = "prefix/year=2025/month=01/day=07"
                save_json_to_s3({"data": "test"}, "raw_subreddits_popular")

        assert "Failed to save JSON" in str(exc_info.value)


class TestSaveParquetToS3:
    def test_saves_dataframe_to_correct_path(self, mocker: Any) -> None:
        """DataFrame should be saved to Hive-style partition path."""
        mock_write = mocker.patch.object(pl.DataFrame, "write_parquet")

        df = pl.DataFrame({"col1": [1, 2, 3]})

        with patch("src.storage.write_to_dest.get_partition_path") as mock_path:
            mock_path.return_value = "popular_subreddits/year=2025/month=01/day=07"
            save_parquet_to_s3(df, "cleaned_subreddits")

        mock_write.assert_called_once()
        s3_path = mock_write.call_args[0][0]

        assert "s3://" in s3_path
        assert "year=2025" in s3_path
        assert s3_path.endswith("/data.parquet")

    def test_converts_list_of_dicts_to_dataframe(self, mocker: Any) -> None:
        """List of dicts should be converted to DataFrame before saving."""
        mock_write = mocker.patch.object(pl.DataFrame, "write_parquet")

        data = [{"name": "test1"}, {"name": "test2"}]

        with patch("src.storage.write_to_dest.get_partition_path") as mock_path:
            mock_path.return_value = "prefix/year=2025/month=01/day=07"
            save_parquet_to_s3(data, "cleaned_subreddits")

        mock_write.assert_called_once()

    def test_write_error_raises_storage_error(self, mocker: Any) -> None:
        """Parquet write errors should be wrapped in StorageError."""
        mocker.patch.object(
            pl.DataFrame,
            "write_parquet",
            side_effect=Exception("S3 write failed"),
        )

        df = pl.DataFrame({"col1": [1, 2, 3]})

        with pytest.raises(StorageError) as exc_info:
            with patch("src.storage.write_to_dest.get_partition_path") as mock_path:
                mock_path.return_value = "prefix/year=2025/month=01/day=07"
                save_parquet_to_s3(df, "cleaned_subreddits")

        assert "Failed to save parquet" in str(exc_info.value)

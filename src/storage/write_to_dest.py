import json
from datetime import UTC, datetime
from typing import Any, Literal

import boto3
import polars as pl
import structlog
from botocore.exceptions import ClientError

from src.config import get_data_path, get_partition_path, get_s3_region
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def save_to_s3(data: Any, data_type_key: str, file_format: Literal["json", "parquet"]) -> None:
    """
    Save data to S3 in the specified format using Hive-style partitioning.
    Path: prefix/year=YYYY/month=MM/day=DD/data.extension

    Args:
        data: The data to save (dict/list for 'json', pl.DataFrame for 'parquet').
        data_type_key: Key used to look up bucket and prefix.
        file_format: The format to save in ('json' or 'parquet').
    """
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix)

    if file_format == "json":
        region = get_s3_region()
        s3_client = boto3.client("s3", region_name=region)
        key = f"{partition_path}/data.json"
        try:
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(data),
                ContentType="application/json",
            )
            logger.info("JSON saved to S3", bucket=bucket, key=key)
            return
        except ClientError as e:
            raise StorageError(
                f"Failed to save JSON to S3: {bucket}/{key}") from e

    if file_format == "parquet":
        if not isinstance(data, pl.DataFrame):
            try:
                data = pl.DataFrame(data)
            except Exception as e:
                raise StorageError(
                    f"Data provided for parquet format is not compatible: {e}") from e

        s3_path = f"s3://{bucket}/{partition_path}/data.parquet"
        try:
            data.write_parquet(s3_path)
            logger.info("Parquet saved to S3", path=s3_path, records=len(data))
            return
        except Exception as e:
            raise StorageError(f"Failed to save parquet to {s3_path}") from e

    raise ValueError(f"Unsupported file format: {file_format}")

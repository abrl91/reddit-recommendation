import json
from datetime import UTC, datetime
from typing import Any

import boto3
import polars as pl
import structlog
from botocore.exceptions import ClientError

from src.config import get_data_path, get_s3_region
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def save_to_s3(data: dict[str, Any], data_type_key: str) -> None:
    bucket, prefix = get_data_path(data_type_key)
    region = get_s3_region()

    s3_client = boto3.client("s3", region_name=region)
    current_date = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"{prefix}_{current_date}.json"

    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data),
            ContentType="application/json",
        )
    except ClientError as e:
        raise StorageError(f"Failed to save '{data_type_key}' to S3: {bucket}/{key}") from e

    logger.info("Data saved to S3", bucket=bucket, key=key)


def save_parquet_to_s3(df: pl.DataFrame, data_type_key: str) -> None:
    bucket, prefix = get_data_path(data_type_key)

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    s3_path = f"s3://{bucket}/{prefix}_{date_str}.parquet"

    try:
        df.write_parquet(s3_path)
    except Exception as e:
        raise StorageError(f"Failed to save parquet to {s3_path}") from e

    logger.info("Parquet saved to S3", path=s3_path, records=len(df))

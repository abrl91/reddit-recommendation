import json
from typing import Any

import boto3
import polars as pl
import structlog
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client

from src.config import (
    SourceType,
    get_bronze_location,
    get_gold_location,
    get_partition_path,
    get_s3_endpoint_url,
    get_s3_region,
    get_silver_location,
    is_localstack,
)
from src.models import RawListingResponse, RawPostResponse
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def _get_s3_client() -> S3Client:
    region = get_s3_region()
    endpoint_url = get_s3_endpoint_url()

    if endpoint_url:
        return boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    return boto3.client("s3", region_name=region)


def _get_polars_storage_options() -> dict[str, Any] | None:
    if is_localstack():
        return {
            "aws_endpoint_url": get_s3_endpoint_url(),
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "aws_region": get_s3_region(),
        }
    return None


def save_bronze(
    data: RawPostResponse | RawListingResponse,
    source: SourceType,
    tag: str,
    include_hour: bool = True,
) -> None:
    bucket, prefix = get_bronze_location(source, tag)
    partition_path = get_partition_path(prefix, include_hour=include_hour)
    s3_client = _get_s3_client()
    key = f"{partition_path}/data.json"

    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data),
            ContentType="application/json",
        )
        logger.info("Bronze saved to S3", bucket=bucket, key=key)
    except ClientError as e:
        raise StorageError(f"Failed to save bronze to S3: {bucket}/{key}") from e


def save_silver(
    data: pl.DataFrame,
    source: SourceType,
    tag: str,
    include_hour: bool = True,
) -> None:
    bucket, prefix = get_silver_location(source, tag)
    partition_path = get_partition_path(prefix, include_hour=include_hour)

    s3_path = f"s3://{bucket}/{partition_path}/data.parquet"
    storage_options = _get_polars_storage_options()

    try:
        data.write_parquet(s3_path, storage_options=storage_options)
        logger.info("Silver saved to S3", path=s3_path, records=len(data))
    except Exception as e:
        raise StorageError(f"Failed to save silver to {s3_path}") from e


def save_gold(
    data: pl.DataFrame,
    source: SourceType,
) -> None:
    bucket, prefix = get_gold_location(source)
    partition_path = get_partition_path(prefix, include_hour=False)

    s3_path = f"s3://{bucket}/{partition_path}/data.parquet"
    storage_options = _get_polars_storage_options()

    try:
        data.write_parquet(s3_path, storage_options=storage_options)
        logger.info("Gold saved to S3", path=s3_path, records=len(data))
    except Exception as e:
        raise StorageError(f"Failed to save gold to {s3_path}") from e

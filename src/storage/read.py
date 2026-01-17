import json
from datetime import datetime
from typing import Any

import boto3
import polars as pl
import structlog
from mypy_boto3_s3 import S3Client

from src.config import (
    SourceType,
    get_bronze_location,
    get_gold_tags,
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


def read_bronze(
    source: SourceType,
    tag: str,
    date: datetime | None = None,
    include_hour: bool = True,
) -> RawPostResponse | RawListingResponse | None:
    bucket, prefix = get_bronze_location(source, tag)
    partition_path = get_partition_path(prefix, date=date, include_hour=include_hour)

    s3_client = _get_s3_client()
    results: list[RawListingResponse | RawPostResponse] = []

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=partition_path)

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]
                if not key.endswith(".json"):
                    continue

                try:
                    file_response = s3_client.get_object(Bucket=bucket, Key=key)
                    content = file_response["Body"].read().decode("utf-8")
                    data: RawListingResponse = json.loads(content)
                    results.append(data)
                except Exception as e:
                    logger.error("Failed to read file from S3", key=key, error=str(e))
                    continue

    except s3_client.exceptions.NoSuchBucket:
        raise StorageError(f"Bucket '{bucket}' does not exist")
    except Exception as e:
        raise StorageError(
            f"Failed to list objects in partition: {bucket}/{partition_path}"
        ) from e

    if results:
        if len(results) > 1:
            logger.warning(
                "Multiple files in partition, using first",
                source=source,
                tag=tag,
                file_count=len(results),
            )
        logger.info(
            "Bronze read from S3",
            bucket=bucket,
            partition=partition_path,
        )
        return results[0]

    logger.warning("No bronze data found", source=source, tag=tag)
    return None


def read_silver(
    source: SourceType,
    tag: str,
    date: datetime | None = None,
    recursive: bool = True,
) -> pl.DataFrame | None:
    bucket, prefix = get_silver_location(source, tag)
    partition_path = get_partition_path(prefix, date=date, include_hour=False)
    glob_pattern = "*/*.parquet" if recursive else "*.parquet"
    s3_url = f"s3://{bucket}/{partition_path}/{glob_pattern}"
    storage_options = _get_polars_storage_options()

    try:
        df = pl.read_parquet(s3_url, storage_options=storage_options)
        logger.info(
            "Silver read from S3",
            bucket=bucket,
            partition=partition_path,
            records=len(df),
        )
        return df
    except Exception as e:
        logger.warning(
            "No silver data found",
            source=source,
            tag=tag,
            url=s3_url,
            error=str(e),
        )
        return None


def read_silver_for_gold(
    source: SourceType,
    date: datetime | None = None,
) -> dict[str, pl.DataFrame]:
    tags = get_gold_tags(source)
    results: dict[str, pl.DataFrame] = {}

    for tag in tags:
        df = read_silver(source, tag, date=date, recursive=True)
        if df is not None:
            results[tag] = df

    logger.info(
        "Read silver for gold merge",
        source=source,
        tags_found=list(results.keys()),
        tags_missing=[t for t in tags if t not in results],
    )
    return results

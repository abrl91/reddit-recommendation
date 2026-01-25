import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

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


@dataclass
class BronzeResult:
    """Result from reading bronze layer, includes source key for lineage tracking."""

    data: RawPostResponse | RawListingResponse
    source_key: str  # e.g., "posts/hot/year=2025/month=01/day=25/hour=14/data.json"

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
) -> BronzeResult | None:
    bucket, prefix = get_bronze_location(source, tag)
    partition_path = get_partition_path(prefix, date=date, include_hour=include_hour)

    s3_client = _get_s3_client()
    results: list[tuple[str, RawListingResponse | RawPostResponse]] = []

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
                    data = cast(RawListingResponse | RawPostResponse, json.loads(content))
                    results.append((key, data))
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
        source_key, data = results[0]
        logger.info(
            "Bronze read from S3",
            bucket=bucket,
            partition=partition_path,
            source_key=source_key,
        )
        return BronzeResult(data=data, source_key=source_key)

    logger.warning("No bronze data found", source=source, tag=tag)
    return None


def read_silver(
    source: SourceType,
    tag: str,
    date: datetime | None = None,
    include_all_hours: bool = True,
) -> pl.DataFrame | None:
    bucket, prefix = get_silver_location(source, tag)
    partition_path = get_partition_path(prefix, date=date, include_hour=False)
    glob_pattern = "*/*.parquet" if include_all_hours else "*.parquet"
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


def collect_silver_for_merge(
    source: SourceType,
    date: datetime | None = None,
) -> dict[str, pl.DataFrame]:
    """Reads all configured silver tags for a source, returning dict[tag, DataFrame]."""
    tags = get_gold_tags(source)
    results: dict[str, pl.DataFrame] = {}

    for tag in tags:
        df = read_silver(source, tag, date=date, include_all_hours=True)
        if df is not None:
            results[tag] = df

    logger.info(
        "Collected silver for merge",
        source=source,
        tags_found=list(results.keys()),
        tags_missing=[t for t in tags if t not in results],
    )
    return results

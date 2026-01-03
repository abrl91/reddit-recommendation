import json
from datetime import datetime

import boto3
import polars as pl
import structlog

from src.config import get_data_path, get_partition_path, get_s3_region
from src.models import SubredditListingResponse
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def read_json_from_s3(data_type_key: str, date: datetime | None = None) -> list[SubredditListingResponse]:
    """
    Read JSON files from a specific Hive-style partition in S3.
    If no date is provided, it defaults to the current day's partition.
    """
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix, date=date)
    region = get_s3_region()

    s3_client = boto3.client("s3", region_name=region)
    results: list[SubredditListingResponse] = []

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
                    file_response = s3_client.get_object(
                        Bucket=bucket, Key=key)
                    content = file_response["Body"].read().decode("utf-8")
                    data: SubredditListingResponse = json.loads(content)
                    results.append(data)
                except Exception as e:
                    logger.error("Failed to read file from S3",
                                 key=key, error=str(e))
                    continue

    except s3_client.exceptions.NoSuchBucket:
        raise StorageError(f"Bucket '{bucket}' does not exist")
    except Exception as e:
        raise StorageError(
            f"Failed to list objects in partition: {bucket}/{partition_path}") from e

    logger.info("Data read from S3 partition", bucket=bucket,
                partition=partition_path, files_read=len(results))
    return results


def read_parquet_from_s3(data_type_key: str, date: datetime | None = None) -> pl.DataFrame:
    """
    Read Parquet files from a specific Hive-style partition in S3 using Polars.
    """
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix, date=date)
    s3_url = f"s3://{bucket}/{partition_path}/*.parquet"

    try:
        df = pl.read_parquet(s3_url)
        logger.info("Parquet read from S3 partition", bucket=bucket,
                    partition=partition_path, records=len(df))
        return df
    except Exception as e:
        logger.error("Failed to read parquet from S3",
                     url=s3_url, error=str(e))
        raise StorageError(f"Failed to read parquet from {s3_url}: {e}") from e

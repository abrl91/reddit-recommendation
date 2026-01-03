import json
from datetime import datetime

import boto3
import structlog

from src.config import get_data_path, get_partition_path, get_s3_region
from src.models import SubredditListingResponse
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def read_from_s3(data_type_key: str, date: datetime | None = None) -> list[SubredditListingResponse]:
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
        response = s3_client.list_objects_v2(
            Bucket=bucket, Prefix=partition_path)

        if "Contents" not in response:
            logger.warning("No files found in partition",
                           bucket=bucket, partition=partition_path)
            return []

        for obj in response["Contents"]:
            key = obj["Key"]
            if not key.endswith(".json"):
                continue

            try:
                file_response = s3_client.get_object(Bucket=bucket, Key=key)
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

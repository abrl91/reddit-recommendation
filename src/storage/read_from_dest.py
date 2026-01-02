import json

import boto3
import structlog

from src.config import get_data_path, get_s3_region
from src.models import SubredditListingResponse
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def read_from_s3(data_type_key: str) -> list[SubredditListingResponse]:
    from_bucket, from_prefix = get_data_path(data_type_key)
    region = get_s3_region()

    s3_client = boto3.client("s3", region_name=region)

    try:
        # todo: improve list object, and handle pagination
        response = s3_client.list_objects_v2(Bucket=from_bucket, Prefix=from_prefix)
    except s3_client.exceptions.NoSuchBucket:
        raise StorageError(f"Bucket '{from_bucket}' does not exist")

    if "Contents" not in response:
        logger.warning("No files found in S3", bucket=from_bucket, prefix=from_prefix)
        return []

    results: list[SubredditListingResponse] = []

    for obj in response["Contents"]:
        key = obj["Key"]
        if not key.endswith(".json"):
            continue

        try:
            file_response = s3_client.get_object(Bucket=from_bucket, Key=key)
            content = file_response["Body"].read().decode("utf-8")
            data: SubredditListingResponse = json.loads(content)
            # todo: content + data existence and result size
            results.append(data)
        except Exception as e:
            raise StorageError(f"Failed to read '{key}' from S3") from e

    logger.info("Data read from S3", bucket=from_bucket, prefix=from_prefix, files_read=len(results))
    return results

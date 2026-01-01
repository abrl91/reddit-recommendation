import json
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..config import get_data_path, get_s3_region
from .exceptions import StorageError


def save_to_s3(data: dict[str, Any], data_type_key: str) -> None:
    """Raises StorageError on failure."""
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

    print(f"Data saved to S3 successfully: s3://{bucket}/{key}")

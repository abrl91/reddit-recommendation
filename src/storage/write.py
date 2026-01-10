import json
import boto3
import polars as pl
import structlog
from botocore.exceptions import ClientError

from src.config import get_data_path, get_partition_path, get_s3_region
from src.models.reddit import SubredditListingResponse
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")


def save_json_to_s3(
    data: SubredditListingResponse, data_type_key: str, include_hour: bool = False
) -> None:
    """Raises StorageError on failure."""
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix, include_hour=include_hour)
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
    except ClientError as e:
        raise StorageError(f"Failed to save JSON to S3: {bucket}/{key}") from e


def save_parquet_to_s3(
    data: pl.DataFrame | list[dict] | dict,
    data_type_key: str,
    include_hour: bool = False,
) -> None:
    """Raises StorageError on failure."""
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix, include_hour=include_hour)

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
    except Exception as e:
        raise StorageError(f"Failed to save parquet to {s3_path}") from e

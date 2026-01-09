import json
from datetime import datetime

import boto3
import polars as pl
import structlog

from src.config import get_data_path, get_partition_path, get_s3_region
from src.models import SourceTag, SubredditListingResponse
from src.storage.exceptions import StorageError

logger = structlog.get_logger().bind(module="storage")

_SOURCE_TO_BRONZE_KEY: dict[SourceTag, str] = {
    SourceTag.POPULAR: "raw_subreddits_popular",
    SourceTag.NEW: "raw_subreddits_new",
    SourceTag.HOT: "raw_subreddits_hot",
    SourceTag.RISING: "raw_subreddits_rising",
}

_SOURCE_TO_SILVER_KEY: dict[SourceTag, str] = {
    SourceTag.POPULAR: "cleaned_subreddits_popular",
    SourceTag.NEW: "cleaned_subreddits_new",
    SourceTag.HOT: "cleaned_subreddits_hot",
    SourceTag.RISING: "cleaned_subreddits_rising",
}


def read_json_from_s3(
    data_type_key: str, date: datetime | None = None, include_hour: bool = False
) -> list[SubredditListingResponse]:
    """Raises StorageError on failure."""
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix, date=date, include_hour=include_hour)
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


def read_parquet_from_s3(
    data_type_key: str, date: datetime | None = None, include_hour: bool = False
) -> pl.DataFrame:
    """Raises StorageError on failure."""
    bucket, prefix = get_data_path(data_type_key)
    partition_path = get_partition_path(prefix, date=date, include_hour=include_hour)
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


def read_bronze_source(
    source: SourceTag, date: datetime | None = None, include_hour: bool = False
) -> SubredditListingResponse | None:
    """Read a single Bronze source. Returns None if no data found."""
    data_key = _SOURCE_TO_BRONZE_KEY[source]
    try:
        responses = read_json_from_s3(data_key, date=date, include_hour=include_hour)
        if responses:
            if len(responses) > 1:
                logger.warning(
                    "Multiple files in partition, using first",
                    source=source,
                    file_count=len(responses),
                )
            return responses[0]
        logger.warning("No data found for source", source=source)
        return None
    except StorageError as e:
        logger.error("Failed to read source", source=source, error=str(e))
        return None


def read_silver_source(
    source: SourceTag, date: datetime | None = None, include_hour: bool = False
) -> pl.DataFrame | None:
    """Read a single Silver source (cleaned parquet). Returns None if not found."""
    data_key = _SOURCE_TO_SILVER_KEY[source]
    try:
        return read_parquet_from_s3(data_key, date=date, include_hour=include_hour)
    except StorageError as e:
        logger.error("Failed to read silver source", source=source, error=str(e))
        return None


def read_all_silver_sources(
    date: datetime | None = None,
) -> dict[SourceTag, pl.DataFrame]:
    """
    Read all 4 Silver sources for Gold merge.
    Reads daily partitions (aggregates all hours).
    Skips sources with no data (logs warning).
    """
    results: dict[SourceTag, pl.DataFrame] = {}

    for source, data_key in _SOURCE_TO_SILVER_KEY.items():
        try:
            # Read all parquet files in the day partition (all hours)
            bucket, prefix = get_data_path(data_key)
            day_path = get_partition_path(prefix, date=date, include_hour=False)
            s3_url = f"s3://{bucket}/{day_path}/**/*.parquet"

            df = pl.read_parquet(s3_url)
            results[source] = df
            logger.info(
                "Read silver source",
                source=source,
                records=len(df),
            )
        except Exception as e:
            logger.warning("No silver data for source", source=source, error=str(e))

    logger.info(
        "Read silver sources for Gold merge",
        sources_found=list(results.keys()),
        sources_missing=[s for s in _SOURCE_TO_SILVER_KEY if s not in results],
    )
    return results


def read_all_subreddit_sources(
    date: datetime | None = None,
) -> dict[SourceTag, SubredditListingResponse]:
    """
    Read all 4 subreddit sources from bronze layer.
    Returns dict mapping source tag to response, ready for clean_multi_source_data().
    Skips sources with no data (logs warning).
    """
    results: dict[SourceTag, SubredditListingResponse] = {}

    for source, data_key in _SOURCE_TO_BRONZE_KEY.items():
        try:
            responses = read_json_from_s3(data_key, date=date)
            if responses:
                # Take first response (each source should have 1 file per partition)
                results[source] = responses[0]
                if len(responses) > 1:
                    logger.warning(
                        "Multiple files in partition, using first",
                        source=source,
                        file_count=len(responses),
                    )
            else:
                logger.warning("No data found for source", source=source)
        except StorageError as e:
            logger.error("Failed to read source", source=source, error=str(e))
            # Continue with other sources - don't fail entire pipeline

    logger.info(
        "Read subreddit sources from bronze",
        sources_found=list(results.keys()),
        sources_missing=[s for s in _SOURCE_TO_BRONZE_KEY if s not in results],
    )

    return results

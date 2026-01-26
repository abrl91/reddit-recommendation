import os
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

import yaml


DataLayer = Literal["bronze", "silver", "gold"]
SourceType = Literal["posts", "communities"]


class BucketsConfig(TypedDict):
    bronze: str
    silver: str
    gold: str


class S3Config(TypedDict):
    region: str
    buckets: BucketsConfig


class StreamConfig(TypedDict):
    sort: str
    limit: int


class GoldConfig(TypedDict):
    tags: list[str]


class EnrichmentConfig(TypedDict):
    active_community_threshold: int


class Config(TypedDict):
    lemmy_api_base_url: str
    s3: S3Config
    data_streams: dict[SourceType, dict[str, StreamConfig]]
    gold: dict[SourceType, GoldConfig]
    enrichment: EnrichmentConfig


@lru_cache
def get_config() -> Config:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    with open(config_path) as f:
        config: Config = yaml.safe_load(f)

    return config


def get_s3_bucket(layer: DataLayer) -> str:
    config = get_config()
    return config["s3"]["buckets"][layer]


def get_s3_region() -> str:
    config = get_config()
    return config["s3"]["region"]


def is_localstack() -> bool:
    return os.environ.get("USE_LOCALSTACK", "").lower() in ("1", "true", "yes")


def get_s3_endpoint_url() -> str | None:
    if is_localstack():
        return os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    return None


def get_lemmy_base_url() -> str:
    config = get_config()
    return config["lemmy_api_base_url"]


def get_stream_config(source: SourceType, tag: str) -> StreamConfig:
    """Raises KeyError if source/tag combination not found."""
    config = get_config()
    return config["data_streams"][source][tag]


def get_stream_path(source: SourceType, tag: str) -> str:
    return f"{source}/{tag}"


SOURCES: tuple[SourceType, ...] = ("posts", "communities")


def get_all_streams() -> list[tuple[SourceType, str, StreamConfig]]:
    config = get_config()
    result: list[tuple[SourceType, str, StreamConfig]] = []
    for source in SOURCES:
        for tag, stream_config in config["data_streams"][source].items():
            result.append((source, tag, stream_config))
    return result


def get_bronze_location(source: SourceType, tag: str) -> tuple[str, str]:
    bucket = get_s3_bucket("bronze")
    prefix = get_stream_path(source, tag)
    return bucket, prefix


def get_silver_location(source: SourceType, tag: str) -> tuple[str, str]:
    bucket = get_s3_bucket("silver")
    prefix = get_stream_path(source, tag)
    return bucket, prefix


def get_gold_location(source: SourceType) -> tuple[str, str]:
    bucket = get_s3_bucket("gold")
    return bucket, source


def get_gold_tags(source: SourceType) -> list[str]:
    config = get_config()
    return config["gold"][source]["tags"]


def get_active_community_threshold() -> int:
    config = get_config()
    return config["enrichment"]["active_community_threshold"]


def get_partition_path(
    prefix: str, date: datetime | None = None, include_hour: bool = False
) -> str:
    """Returns Hive-style path: prefix/year=.../month=.../day=.../[hour=...]"""
    dt = date or datetime.now(UTC)
    path = f"{prefix}/year={dt.year}/month={dt.month:02d}/day={dt.day:02d}"
    if include_hour:
        path = f"{path}/hour={dt.hour:02d}"
    return path

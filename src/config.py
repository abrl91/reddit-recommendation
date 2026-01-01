from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

import yaml


DataLayer = Literal["bronze", "silver", "gold"]


class BucketsConfig(TypedDict, total=False):
    bronze: str
    silver: str
    gold: str


class S3Config(TypedDict):
    region: str
    buckets: BucketsConfig


class DataPathConfig(TypedDict):
    layer: DataLayer
    prefix: str


class Config(TypedDict):
    s3: S3Config
    data_paths: dict[str, DataPathConfig]


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


def get_data_path(data_type_key: str) -> tuple[str, str]:
    """Returns (bucket_name, prefix). Raises KeyError if data_type not found."""
    config = get_config()
    data_config = config["data_paths"][data_type_key]
    layer = get_s3_bucket(data_config["layer"])
    prefix = data_config["prefix"]
    return layer, prefix

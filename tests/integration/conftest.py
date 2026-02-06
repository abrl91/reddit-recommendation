import os
from typing import Generator
import time

import boto3
import pytest
from mypy_boto3_s3 import S3Client

LOCALSTACK_ENDPOINT = "http://localhost:4566"
TEST_BUCKETS = ["lemmy-bronze-data", "lemmy-silver-data", "lemmy-gold-data"]


@pytest.fixture(scope="session", autouse=True)
def setup_localstack_env() -> Generator[None, None, None]:
    """Set environment for LocalStack before any imports use config."""
    os.environ["USE_LOCALSTACK"] = "true"
    os.environ["LOCALSTACK_ENDPOINT"] = LOCALSTACK_ENDPOINT
    yield


@pytest.fixture(scope="session")
def localstack_s3() -> Generator[S3Client, None, None]:
    """S3 client with bucket setup. Waits for LocalStack to be ready."""
    client: S3Client = boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )

    for _ in range(30):
        try:
            client.list_buckets()
            break
        except Exception:
            time.sleep(1)
    else:
        pytest.fail("LocalStack not ready after 30s")

    for bucket in TEST_BUCKETS:
        try:
            client.create_bucket(Bucket=bucket)
        except client.exceptions.BucketAlreadyOwnedByYou:
            pass

    yield client


@pytest.fixture
def clean_buckets(localstack_s3: S3Client) -> Generator[S3Client, None, None]:
    """Empty all test buckets before each test for isolation."""
    for bucket in TEST_BUCKETS:
        try:
            resp = localstack_s3.list_objects_v2(Bucket=bucket)
            for obj in resp.get("Contents", []):
                localstack_s3.delete_object(Bucket=bucket, Key=obj["Key"])
        except Exception:
            pass
    yield localstack_s3

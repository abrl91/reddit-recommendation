from datetime import datetime

import structlog

from src.ingestion.exceptions import IngestionError
from src.ingestion.fetch_reddit import (
    fetch_hot_subreddits,
    fetch_new_subreddits,
    fetch_popular_subreddits,
    fetch_rising_subreddits,
)
from src.models import SourceTag
from src.storage import (
    SOURCE_TO_BRONZE_KEY,
    SOURCE_TO_SILVER_KEY,
    StorageError,
    read_all_silver_sources,
    read_bronze_source,
    save_json_to_s3,
    save_parquet_to_s3,
)
from src.transformation import (
    DataQualityError,
    TransformationError,
    clean_source_data,
)
from src.transformation.merge_datasources import merge_silver_sources

logger = structlog.get_logger()

_SOURCE_TO_FETCH_FN = {
    SourceTag.POPULAR: fetch_popular_subreddits,
    SourceTag.NEW: fetch_new_subreddits,
    SourceTag.HOT: fetch_hot_subreddits,
    SourceTag.RISING: fetch_rising_subreddits,
}


def create_bronze_source(source: SourceTag) -> None:
    """Fetch single source from Reddit API and save to Bronze with hourly partition."""
    log = logger.bind(layer="bronze", source=source)
    log.info("Creating bronze for source")

    try:
        fetch_fn = _SOURCE_TO_FETCH_FN[source]
        data_key = SOURCE_TO_BRONZE_KEY[source]

        raw_data = fetch_fn()
        save_json_to_s3(raw_data, data_key, include_hour=True)
        log.info("Bronze created successfully")
    except IngestionError as e:
        log.error("Ingestion failed", error=str(e))
        raise
    except StorageError as e:
        log.error("Storage failed", error=str(e))
        raise


def create_silver_source(source: SourceTag) -> None:
    """Read single Bronze source, clean, and save to Silver with hourly partition."""
    log = logger.bind(layer="silver", source=source)
    log.info("Creating silver for source")

    try:
        bronze_data = read_bronze_source(source, include_hour=True)

        if bronze_data is None:
            log.error("No bronze data found for source")
            raise StorageError(f"No bronze data available for {source}")

        clean_data = clean_source_data(bronze_data, source)
        silver_key = SOURCE_TO_SILVER_KEY[source]
        save_parquet_to_s3(clean_data, silver_key, include_hour=True)
        log.info("Silver created successfully", records=len(clean_data))
    except StorageError as e:
        log.error("Storage failed", error=str(e))
        raise
    except TransformationError as e:
        log.error("Transformation failed", error=str(e), step=e.step)
        raise
    except DataQualityError as e:
        log.error("Data quality check failed", error=str(e))
        raise


def create_gold(date: datetime | None = None) -> None:
    """Read all Silver sources for a day, merge, and save to Gold."""
    log = logger.bind(layer="gold")
    log.info("Creating gold layer", date=date)

    try:
        silver_data = read_all_silver_sources(date=date)

        if not silver_data:
            log.error("No silver data found for any source")
            raise StorageError("No silver data available for Gold merge")

        merged_data = merge_silver_sources(silver_data)
        save_parquet_to_s3(merged_data, "merged_subreddits",
                           include_hour=False)
        log.info(
            "Gold created successfully",
            records=len(merged_data),
            sources=list(silver_data.keys()),
        )
    except StorageError as e:
        log.error("Storage failed", error=str(e))
        raise
    except TransformationError as e:
        log.error("Transformation failed", error=str(e), step=e.step)
        raise
    except DataQualityError as e:
        log.error("Data quality check failed", error=str(e))
        raise


def main() -> None:
    """Run full pipeline: Bronze → Silver for all sources, then Gold merge."""
    logger.info("reddit-recommendation pipeline starting")

    for source in SourceTag:
        create_bronze_source(source)
        create_silver_source(source)

    create_gold()

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    main()

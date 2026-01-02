import structlog

from src.data_ingestion.exceptions import IngestionError
from src.data_ingestion.fetch_reddit import fetch_popular_subreddits
from src.data_transformation import TransformationError, clean_raw_data
from src.storage import StorageError, read_from_s3, save_parquet_to_s3, save_to_s3

logger = structlog.get_logger()


def create_bronze() -> None:
    log = logger.bind(layer="bronze")
    log.info("Creating bronze layer")
    try:
        raw_data = fetch_popular_subreddits()
        save_to_s3(raw_data, "raw_popular_subreddits")
        log.info("Bronze layer created successfully")
    except IngestionError as e:
        log.error("Ingestion failed", error=str(e))
    except StorageError as e:
        log.error("Storage failed", error=str(e))


def create_silver() -> None:
    log = logger.bind(layer="silver")
    log.info("Creating silver layer")
    try:
        raw_data = read_from_s3("raw_popular_subreddits")
        clean_data = clean_raw_data(raw_data)
        save_parquet_to_s3(clean_data, "cleaned_popular_subreddits")
        log.info("Silver layer created successfully")
    except StorageError as e:
        log.error("Storage failed", error=str(e))
    except TransformationError as e:
        log.error("Transformation failed", error=str(e), step=e.step, record_count=e.record_count)


def main() -> None:
    logger.info("reddit-recommendation is running")
    create_bronze()
    create_silver()


if __name__ == "__main__":
    main()

import structlog

from src.data_ingestion.exceptions import IngestionError
from src.data_ingestion.fetch_reddit import (
    fetch_hot_subreddits,
    fetch_new_subreddits,
    fetch_popular_subreddits,
    fetch_rising_subreddits,
)
from src.data_transformation import (
    DataQualityError,
    TransformationError,
    clean_multi_source_data,
)
from src.models import SourceTag
from src.storage import (
    StorageError,
    read_all_subreddit_sources,
    save_json_to_s3,
    save_parquet_to_s3,
)

logger = structlog.get_logger()


def create_bronze() -> None:
    """Fetch from all 4 Reddit sources and save to bronze layer."""
    log = logger.bind(layer="bronze")
    log.info("Creating bronze layer from 4 sources")

    # Map source tag to (fetch_function, data_key)
    sources = [
        (SourceTag.POPULAR, fetch_popular_subreddits, "raw_subreddits_popular"),
        (SourceTag.NEW, fetch_new_subreddits, "raw_subreddits_new"),
        (SourceTag.HOT, fetch_hot_subreddits, "raw_subreddits_hot"),
        (SourceTag.RISING, fetch_rising_subreddits, "raw_subreddits_rising"),
    ]

    for source_tag, fetch_fn, data_key in sources:
        try:
            log.info("Fetching source", source=source_tag)
            raw_data = fetch_fn()
            save_json_to_s3(raw_data, data_key)
            log.info("Source saved to bronze", source=source_tag)
        except IngestionError as e:
            log.error("Ingestion failed for source", source=source_tag, error=str(e))
            raise
        except StorageError as e:
            log.error("Storage failed for source", source=source_tag, error=str(e))
            raise

    log.info("Bronze layer created successfully", sources_count=len(sources))


def create_silver() -> None:
    """Read all bronze sources, merge with source tagging, save to silver."""
    log = logger.bind(layer="silver")
    log.info("Creating silver layer")

    try:
        sources_data = read_all_subreddit_sources()

        if not sources_data:
            log.error("No data found in any bronze source")
            raise StorageError("No bronze data available for transformation")

        clean_data = clean_multi_source_data(sources_data)
        save_parquet_to_s3(clean_data, "cleaned_subreddits")
        log.info(
            "Silver layer created successfully",
            records=len(clean_data),
            sources=list(sources_data.keys()),
        )
    except StorageError as e:
        log.error("Storage failed", error=str(e))
        raise
    except TransformationError as e:
        log.error(
            "Transformation failed",
            error=str(e),
            step=e.step,
            record_count=e.record_count,
        )
        raise
    except DataQualityError as e:
        log.error("Data quality check failed", error=str(e))
        raise


def main() -> None:
    logger.info("reddit-recommendation is running")
    
    create_bronze()
    create_silver()


if __name__ == "__main__":
    main()

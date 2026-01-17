from src.transformation.merge_datasources import merge_silver_sources
from src.transformation import (
    DataQualityError,
    TransformationError,
    clean_source_data,
)
from src.storage import (
    StorageError,
    collect_silver_for_merge,
    read_bronze,
    save_bronze,
    save_gold,
    save_silver,
)
from src.ingestion.fetch_lemmy import fetch
from src.ingestion.exceptions import IngestionError
from src.config import SOURCES, SourceType, get_all_streams
import structlog
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


logger = structlog.get_logger()


def create_bronze_source(source: SourceType, tag: str) -> None:
    logger.info("Creating bronze", layer="bronze", source=source, tag=tag)

    try:
        data = fetch(source, tag)
        save_bronze(data, source, tag, include_hour=True)
        logger.info(
            "Bronze created successfully", layer="bronze", source=source, tag=tag
        )

    except IngestionError as e:
        logger.error(
            "Ingestion failed", layer="bronze", source=source, tag=tag, error=str(e)
        )
        raise


def create_silver_source(source: SourceType, tag: str) -> None:
    log = logger.bind(layer="silver", source=source, tag=tag)
    log.info("Creating silver")

    try:
        bronze_data = read_bronze(source, tag, include_hour=True)

        if bronze_data is None:
            log.error("No bronze data found")
            raise StorageError(f"No bronze data available for {source}/{tag}")

        clean_data = clean_source_data(bronze_data, source, tag)
        save_silver(clean_data, source, tag, include_hour=True)
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


def create_gold(source: SourceType, date: datetime | None = None) -> None:
    log = logger.bind(layer="gold", source=source)
    log.info("Creating gold layer", date=date)

    try:
        silver_data = collect_silver_for_merge(source, date=date)

        if not silver_data:
            log.error("No silver data found for any tag")
            raise StorageError(
                f"No silver data available for {source} Gold merge")

        merged_data = merge_silver_sources(silver_data)
        save_gold(merged_data, source)
        log.info(
            "Gold created successfully",
            records=len(merged_data),
            tags=list(silver_data.keys()),
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
    logger.info("lemmy-recommendation pipeline starting")

    for source, tag, _config in get_all_streams():
        create_bronze_source(source, tag)
        create_silver_source(source, tag)

    for source in SOURCES:
        create_gold(source)

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    main()

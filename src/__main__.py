from datetime import datetime

import structlog
from dotenv import load_dotenv

from src.config import SOURCES, SourceType, get_all_streams
from src.ingestion.exceptions import IngestionError
from src.ingestion.fetch_lemmy import fetch
from src.pipeline import RunContext
from src.storage import (
    StorageError,
    collect_silver_for_merge,
    read_bronze,
    save_bronze,
    save_gold,
    save_silver,
)
from src.transformation import (
    DataQualityError,
    TransformationError,
    clean_source_data,
)
from src.transformation.merge_datasources import merge_silver_sources

load_dotenv()


logger = structlog.get_logger()


def create_bronze_source(source: SourceType, tag: str, run_ctx: RunContext) -> None:
    logger.info(
        "Creating bronze",
        layer="bronze",
        source=source,
        tag=tag,
        run_id=run_ctx.run_id,
    )

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


def create_silver_source(source: SourceType, tag: str, run_ctx: RunContext) -> None:
    log = logger.bind(layer="silver", source=source, tag=tag, run_id=run_ctx.run_id)
    log.info("Creating silver")

    try:
        bronze_result = read_bronze(source, tag, include_hour=True)

        if bronze_result is None:
            log.error("No bronze data found")
            raise StorageError(f"No bronze data available for {source}/{tag}")

        clean_data = clean_source_data(
            bronze_result.data,
            source,
            tag,
            source_file=bronze_result.source_key,
            run_id=run_ctx.run_id,
        )
        save_silver(clean_data, source, tag, include_hour=True)
        log.info(
            "Silver created successfully",
            records=len(clean_data),
            source_file=bronze_result.source_key,
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


def create_gold(
    source: SourceType, run_ctx: RunContext, date: datetime | None = None
) -> None:
    log = logger.bind(layer="gold", source=source, run_id=run_ctx.run_id)
    log.info("Creating gold layer", date=date)

    try:
        silver_data = collect_silver_for_merge(source, date=date)

        if not silver_data:
            log.error("No silver data found for any tag")
            raise StorageError(
                f"No silver data available for {source} Gold merge")

        merged_data = merge_silver_sources(silver_data, run_id=run_ctx.run_id)
        save_gold(merged_data, source)
        log.info(
            "Gold created successfully",
            records=len(merged_data),
            tags=list(silver_data.keys()),
            run_id=run_ctx.run_id,
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
    run_ctx = RunContext.create()
    logger.info("Pipeline starting", run_id=run_ctx.run_id)

    for source, tag, _config in get_all_streams():
        create_bronze_source(source, tag, run_ctx)
        create_silver_source(source, tag, run_ctx)

    for source in SOURCES:
        create_gold(source, run_ctx)

    logger.info("Pipeline completed successfully", run_id=run_ctx.run_id)


if __name__ == "__main__":
    main()

"""
Lemmy Data Pipeline DAGs

18 DAGs using Airflow Datasets for event-driven orchestration:
- 16 Source DAGs: Fetch from Lemmy API → Bronze → Silver (each produces a Dataset)
- 2 Gold DAGs: Triggered when all Silver datasets for a source type are updated

Dataset Flow:
    posts_hot_dag ──────► silver_posts_hot ──────┐
    posts_new_dag ──────► silver_posts_new ──────┤
    ...                                          ├──► posts_gold_dag
    posts_most_comments ► silver_posts_most... ──┘

    communities_hot_dag ► silver_communities_hot ┐
    communities_new_dag ► silver_communities_new ┼──► communities_gold_dag
    ...                                          ┘
"""

from datetime import datetime, timedelta

from airflow.datasets import Dataset
from airflow.decorators import dag, task

from src import create_bronze_source, create_gold, create_silver_source
from src.config import SOURCES, SourceType, get_all_streams, get_s3_bucket

TAG_SCHEDULES: dict[str, timedelta] = {
    # High-frequency: content changes rapidly
    "hot": timedelta(hours=3),
    "active": timedelta(hours=3),
    "scaled": timedelta(hours=3),
    # Medium-frequency
    "new": timedelta(hours=4),
    "most_comments": timedelta(hours=6),
    "top_day": timedelta(hours=8),
    # Low-frequency: aggregated content, slower to change
    "top_week": timedelta(hours=12),
    "top_month": timedelta(hours=12),
    "top_year": timedelta(hours=12),
    "top_all": timedelta(hours=12),
}

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _build_dataset_uri(source: SourceType, tag: str) -> str:
    """Build S3 URI for a silver dataset."""
    bucket = get_s3_bucket("silver")
    return f"s3://{bucket}/{source}/{tag}"


SILVER_DATASETS: dict[tuple[SourceType, str], Dataset] = {
    (source, tag): Dataset(_build_dataset_uri(source, tag))
    for source, tag, _ in get_all_streams()
}


def _get_datasets_for_source(source: SourceType) -> list[Dataset]:
    """Get all silver datasets for a given source type."""
    return [
        dataset
        for (src, _tag), dataset in SILVER_DATASETS.items()
        if src == source
    ]


def create_source_dag(
    source: SourceType,
    tag: str,
    schedule: timedelta,
    outlet_dataset: Dataset,
) -> None:
    """Factory function to create a source DAG (bronze → silver)."""

    @dag(
        dag_id=f"lemmy_{source}_{tag}_pipeline",
        description=f"Fetch {source}/{tag} from Lemmy: Bronze → Silver",
        schedule=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=DEFAULT_ARGS,
        tags=["lemmy", "etl", source, tag],
    )
    def source_pipeline() -> None:
        @task
        def bronze() -> None:
            create_bronze_source(source, tag)

        @task(outlets=[outlet_dataset])
        def silver() -> None:
            create_silver_source(source, tag)

        bronze() >> silver()

    # Register DAG in globals so Airflow discovers it
    dag_instance = source_pipeline()
    globals()[f"lemmy_{source}_{tag}_dag"] = dag_instance


def create_gold_dag(source: SourceType) -> None:
    """Factory function to create a gold DAG triggered by all silver datasets."""
    trigger_datasets = _get_datasets_for_source(source)

    @dag(
        dag_id=f"lemmy_{source}_gold_pipeline",
        description=f"Merge all {source} Silver sources into Gold layer",
        schedule=trigger_datasets,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=DEFAULT_ARGS,
        tags=["lemmy", "etl", "gold", source],
    )
    def gold_pipeline() -> None:
        @task
        def merge_to_gold() -> None:
            create_gold(source)

        merge_to_gold()

    dag_instance = gold_pipeline()
    globals()[f"lemmy_{source}_gold_dag"] = dag_instance


for source, tag, _config in get_all_streams():
    schedule = TAG_SCHEDULES.get(tag, timedelta(days=1))
    outlet_dataset = SILVER_DATASETS[(source, tag)]
    create_source_dag(source, tag, schedule, outlet_dataset)

for source in SOURCES:
    create_gold_dag(source)

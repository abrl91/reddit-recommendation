"""
Reddit Data Pipeline DAGs

5 DAGs using Airflow Datasets for event-driven orchestration:
- 4 Source DAGs: Fetch from Reddit API → Bronze → Silver (each produces a Dataset)
- 1 Gold DAG: Triggered when all Silver datasets are updated → Merges to Gold

Dataset Flow:
    popular_dag ──► silver_popular_dataset ──┐
    new_dag ──────► silver_new_dataset ──────┼──► gold_dag (when ALL 4 updated)
    hot_dag ──────► silver_hot_dataset ──────┤
    rising_dag ───► silver_rising_dataset ───┘
"""

from datetime import datetime, timedelta

from airflow.datasets import Dataset
from airflow.decorators import dag, task

from src import create_bronze_source, create_gold, create_silver_source
from src.models import SourceTag

SILVER_POPULAR_DATASET = Dataset("s3://reddit-data-silver/subreddits/popular")
SILVER_NEW_DATASET = Dataset("s3://reddit-data-silver/subreddits/new")
SILVER_HOT_DATASET = Dataset("s3://reddit-data-silver/subreddits/hot")
SILVER_RISING_DATASET = Dataset("s3://reddit-data-silver/subreddits/rising")

ALL_SILVER_DATASETS = [
    SILVER_POPULAR_DATASET,
    SILVER_NEW_DATASET,
    SILVER_HOT_DATASET,
    SILVER_RISING_DATASET,
]

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def create_source_dag(
    source: SourceTag,
    schedule: timedelta,
    outlet_dataset: Dataset,
):
    @dag(
        dag_id=f"reddit_{source}_pipeline",
        description=f"Fetch {source} subreddits: Bronze → Silver",
        schedule=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=DEFAULT_ARGS,
        tags=["reddit", "etl", source],
    )
    def source_pipeline():
        @task
        def bronze():
            create_bronze_source(source)

        @task(outlets=[outlet_dataset])
        def silver():
            create_silver_source(source)

        bronze() >> silver()

    return source_pipeline()


reddit_popular_dag = create_source_dag(
    source=SourceTag.POPULAR,
    schedule=timedelta(days=1),
    outlet_dataset=SILVER_POPULAR_DATASET,
)

reddit_new_dag = create_source_dag(
    source=SourceTag.NEW,
    schedule=timedelta(days=1),
    outlet_dataset=SILVER_NEW_DATASET,
)

reddit_hot_dag = create_source_dag(
    source=SourceTag.HOT,
    schedule=timedelta(hours=1),
    outlet_dataset=SILVER_HOT_DATASET,
)

reddit_rising_dag = create_source_dag(
    source=SourceTag.RISING,
    schedule=timedelta(hours=2),
    outlet_dataset=SILVER_RISING_DATASET,
)


@dag(
    dag_id="reddit_gold_pipeline",
    description="Merge all Silver sources into Gold layer",
    schedule=ALL_SILVER_DATASETS,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["reddit", "etl", "gold"],
)
def reddit_gold_pipeline():
    @task
    def merge_to_gold():
        """Read all Silver sources, merge, and save to Gold layer."""
        create_gold()

    merge_to_gold()


reddit_gold_dag = reddit_gold_pipeline()

"""
Reddit Data Pipeline DAGs - Medallion Architecture

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

# ---------------------------------------------------------------------------
# Dataset Definitions
# URIs are logical identifiers - Airflow doesn't access them, just tracks updates
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Default Arguments
# ---------------------------------------------------------------------------
DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


# ---------------------------------------------------------------------------
# Source DAG Factory
# Creates Bronze → Silver pipeline for a single source
# ---------------------------------------------------------------------------
def create_source_dag(
    source: SourceTag,
    schedule: str | None,
    outlet_dataset: Dataset,
):
    """Factory function to create a source-specific Bronze → Silver DAG."""

    @dag(
        dag_id=f"reddit_{source.value}_pipeline",
        description=f"Fetch {source.value} subreddits: Bronze → Silver",
        schedule=schedule,
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=DEFAULT_ARGS,
        tags=["reddit", "etl", source.value],
    )
    def source_pipeline():
        @task
        def bronze():
            """Fetch from Reddit API and save to Bronze layer."""
            create_bronze_source(source)

        @task(outlets=[outlet_dataset])
        def silver():
            """Read Bronze, clean, and save to Silver layer."""
            create_silver_source(source)

        bronze() >> silver()

    return source_pipeline()


# ---------------------------------------------------------------------------
# Create the 4 Source DAGs
# ---------------------------------------------------------------------------
# Popular & New: Daily at 6 AM UTC (lower frequency, stable data)
reddit_popular_dag = create_source_dag(
    source=SourceTag.POPULAR,
    schedule="0 6 * * *",  # Daily at 6 AM UTC
    outlet_dataset=SILVER_POPULAR_DATASET,
)

reddit_new_dag = create_source_dag(
    source=SourceTag.NEW,
    schedule="0 6 * * *",  # Daily at 6 AM UTC
    outlet_dataset=SILVER_NEW_DATASET,
)

# Hot: Hourly (changes frequently)
reddit_hot_dag = create_source_dag(
    source=SourceTag.HOT,
    schedule="0 * * * *",  # Every hour
    outlet_dataset=SILVER_HOT_DATASET,
)

# Rising: Every 2 hours (moderate frequency)
reddit_rising_dag = create_source_dag(
    source=SourceTag.RISING,
    schedule="0 */2 * * *",  # Every 2 hours
    outlet_dataset=SILVER_RISING_DATASET,
)


# ---------------------------------------------------------------------------
# Gold DAG - Triggered by ALL Silver Datasets
# ---------------------------------------------------------------------------
@dag(
    dag_id="reddit_gold_pipeline",
    description="Merge all Silver sources into Gold layer",
    schedule=ALL_SILVER_DATASETS,  # Triggers when ALL 4 datasets are updated
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

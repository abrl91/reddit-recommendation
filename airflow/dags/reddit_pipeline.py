from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.data_ingestion.fetch_reddit import fetch_popular_subreddits
from src.data_transformation import clean_raw_data
from src.storage import read_json_from_s3, save_json_to_s3, save_parquet_to_s3


def create_bronze() -> None:
    raw_data = fetch_popular_subreddits()
    save_json_to_s3(raw_data, "raw_popular_subreddits")


def create_silver() -> None:
    raw_data = read_json_from_s3("raw_popular_subreddits")
    clean_data = clean_raw_data(raw_data)
    save_parquet_to_s3(clean_data, "cleaned_popular_subreddits")


with DAG(
    dag_id="reddit_pipeline",
    description="Fetch Reddit subreddits and transform to silver layer",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["reddit", "etl"],
) as dag:

    fetch_task = PythonOperator(
        task_id="fetch_reddit",
        python_callable=create_bronze,
    )

    transform_task = PythonOperator(
        task_id="transform_reddit",
        python_callable=create_silver,
    )

    fetch_task >> transform_task

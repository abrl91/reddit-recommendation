from .data_ingestion.exceptions import IngestionError
from .data_ingestion.fetch_reddit import fetch_popular_subreddits
from .data_transformation import TransformationError, clean_raw_data
from .storage import StorageError, read_from_s3, save_parquet_to_s3, save_to_s3


def create_bronze():
    print("Creating bronze layer...")
    try:
        raw_data = fetch_popular_subreddits()
        save_to_s3(raw_data, "raw_popular_subreddits")
    except IngestionError as e:
        print(f"Ingestion error: {e}")
    except StorageError as e:
        print(f"Storage error: {e}")


def create_silver():
    print("Creating silver layer...")
    try:
        raw_data = read_from_s3("raw_popular_subreddits")
        clean_data = clean_raw_data(raw_data)
        save_parquet_to_s3(clean_data, "cleaned_popular_subreddits")
    except StorageError as e:
        print(f"Storage error: {e}")
    except TransformationError as e:
        print(f"Transformation error: {e}")
    

def main() -> None:
    print("reddit-recommendation is running!")
    create_bronze()
    create_silver()


if __name__ == "__main__":
    main()

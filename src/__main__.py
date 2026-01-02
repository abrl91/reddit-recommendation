from .data_ingestion.exceptions import IngestionError
from .data_ingestion.fetch_reddit import fetch_popular_subreddits
from .data_transformation import clean_raw_data
from .storage import save_to_s3, read_from_s3, StorageError, save_parquet_to_s3


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
        row_data = read_from_s3("raw_popular_subreddits")
        clean_data = clean_raw_data(row_data)
        save_parquet_to_s3(clean_data, "cleaned_popular_subreddits")

    except StorageError as e:
        print(f"Storage error: {e}")
    

def main() -> None:
    print("reddit-recommendation is running!")
    create_bronze()
    create_silver()


if __name__ == "__main__":
    main()

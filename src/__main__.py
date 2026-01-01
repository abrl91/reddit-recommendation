from .data_ingestion.exceptions import IngestionError
from .data_ingestion.fetch_reddit import fetch_popular_subreddits
from .storage.exceptions import StorageError
from .storage.write_to_dest import save_to_s3


def main() -> None:
    print("Hello from reddit-recommendation!")
    try:
        raw_data = fetch_popular_subreddits()
        save_to_s3(raw_data, "popular_subreddits")
        print("Done!")
    except IngestionError as e:
        print(f"Ingestion error: {e}")
    except StorageError as e:
        print(f"Storage error: {e}")


if __name__ == "__main__":
    main()

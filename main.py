import httpx
import boto3
import json
from botocore.exceptions import ClientError
from datetime import datetime

def fetch_popular_subreddits():
    url = "https://www.reddit.com/r/popular.json"
    headers = {
        "User-Agent": "reddit-recommendation/1.0"
    }
    response = httpx.get(url, headers=headers)
    
    if response.status_code == 200:
        raw_data = response.json()
        return raw_data
    
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")


def save_to_s3(data):
    s3_client = boto3.client('s3')
    current_date = datetime.now().strftime("%Y-%m-%d")
    try:
        s3_client.put_object(
            Bucket='reddit-data-bronze-d271225',
            Key=f'popular_subreddits_{current_date}.json',
            Body=json.dumps(data),
            ContentType='application/json'
        )
        print("Data saved to S3 successfully!")
    except ClientError as e:
        print(f"Failed to save data to S3: {e}")



def main():
    print("Hello from reddit-recommendation!")
    raw_data = fetch_popular_subreddits()
    if raw_data:
        save_to_s3(raw_data)
    print("Done!")



if __name__ == "__main__":
    main()

import os
import json
from datetime import datetime
import requests
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

BASE_URL = "https://fakestoreapi.com"
S3_BUCKET = os.getenv("S3_BUCKET_NAME", None)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def fetch_api_data(endpoint: str) -> list:
    """Fetch raw JSON from FakeStore API."""
    url = f"{BASE_URL}/{endpoint}"
    print(f"Fetching: {url}")
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def save_as_parquet(data: list, entity_name: str, output_dir: str = "data") -> str:
    """Convert JSON to Parquet and save locally."""
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame(data)

    # Add ingestion timestamp for audit tracking
    df["_ingested_at"] = datetime.utcnow()

    file_path = os.path.join(output_dir, f"{entity_name}.parquet")
    df.to_parquet(file_path, engine="pyarrow", index=False)
    print(f"Saved: {file_path} ({len(df)} rows)")
    return file_path


def upload_to_s3(local_file_path: str, bucket_name: str, s3_key: str):
    """Upload Parquet file to AWS S3 (Bronze Layer)."""
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    try:
        s3_client.upload_file(local_file_path, bucket_name, s3_key)
        print(f"Uploaded to s3://{bucket_name}/{s3_key}")
    except NoCredentialsError:
        print("Warning: AWS credentials not found. File saved locally only.")
    except Exception as e:
        print(f"Failed to upload to S3: {e}")


def run_pipeline():
    print("=== Starting E-Commerce Ingestion Pipeline ===")
    
    # 1. Endpoints to pull
    endpoints = ["products", "carts", "users"]
    
    for endpoint in endpoints:
        raw_data = fetch_api_data(endpoint)
        local_file = save_as_parquet(raw_data, endpoint)

        # 2. Upload to S3 if a bucket is specified
        if S3_BUCKET:
            # We partition by date: bronze/<endpoint>/year=YYYY/month=MM/
            today = datetime.utcnow()
            s3_key = (
                f"bronze/{endpoint}/"
                f"year={today.year}/month={today.month:02d}/"
                f"{endpoint}.parquet"
            )
            upload_to_s3(local_file, S3_BUCKET, s3_key)
            
    print("=== Pipeline Complete! ===")


if __name__ == "__main__":
    run_pipeline()
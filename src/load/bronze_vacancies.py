import pandas as pd
from deltalake import write_deltalake
from src.storage.s3_client import s3_client
from dotenv import load_dotenv
import json
import os

load_dotenv()


def run_bronze_load(s3_key: str):
    # read the specific raw file extract just wrote
    raw = s3_client.extract_file(s3_key)
    vacancies = raw["data"]
    fetched_at = raw["fetched_at"]

    df = pd.DataFrame(vacancies)
    df["fetched_at"] = fetched_at

    # serialize nested dicts/lists to JSON strings
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            df[col] = df[col].apply(
                lambda x: json.dumps(
                    x, ensure_ascii=False) if x is not None else None
            )

    # fix fully null columns
    for col in df.columns:
        if df[col].isnull().all():
            df[col] = df[col].astype(pd.StringDtype())

    write_deltalake(
        f"s3://{os.getenv('S3_BUCKET_NAME')}/bronze/hh_vacancies",
        df,
        mode="append",
        storage_options={
            "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
            "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "AWS_REGION": os.getenv("AWS_REGION"),
            "AWS_SESSION_TOKEN": "",
            "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
            "AWS_EC2_METADATA_DISABLED": "true",  # disable metadata credential discovery
            "aws_virtual_hosted_style_request": "true",
        }
    )

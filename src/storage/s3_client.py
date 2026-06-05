import boto3
import botocore.exceptions
from datetime import datetime, timezone
import json
import logging
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)


class S3Client:
    def __init__(self, region_name, access_key, secret_key, bucket_name=None):
        self.s3 = boto3.client(
            's3',
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.bucket_name = bucket_name

    def upload_file(self, data, object_name, ds=None):
        if ds is None:
            ds = datetime.now(timezone.utc)

        if object_name == "vacancies":
            key = (
                f"{object_name}/"
                f"year={ds.strftime('%Y')}/"
                f"month={ds.strftime('%m')}/"
                f"day={ds.strftime('%d')}/"
                f"{ds.strftime('%H%M')}.json"
            )
            raw_data = {
                "fetched_at": ds.isoformat(),
                "data": data
            }
        else:
            raise ValueError(f"Unknown object_name: '{object_name}'")

        body = json.dumps(raw_data, ensure_ascii=False).encode('utf-8')

        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType='application/json'
            )
            logger.info("Uploaded to s3://%s/%s", self.bucket_name, key)

            return key

        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
            logger.error("S3 upload failed for key %s: %s",
                         key, e, exc_info=True)
            raise RuntimeError(f"S3 upload failed: {e}")

    def extract_file(self, key):
        try:
            obj = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return json.loads(obj["Body"].read().decode("utf-8"))
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
            logger.error("S3 read failed for key %s: %s",
                         key, e, exc_info=True)
            raise RuntimeError(f"S3 read failed: {e}")


s3_client = S3Client(
    region_name=os.getenv("AWS_REGION"),
    access_key=os.getenv("AWS_ACCESS_KEY_ID"),
    secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    bucket_name=os.getenv("S3_BUCKET_NAME")
)

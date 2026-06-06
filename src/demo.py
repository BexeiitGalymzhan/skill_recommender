from deltalake import DeltaTable
from dotenv import load_dotenv
import os

load_dotenv()

# Define your S3 table URI
s3_uri = "s3://skill-expert/bronze/hh_vacancies"

# Define your AWS credentials and storage settings
storage_options = {
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AWS_REGION": os.getenv("AWS_REGION"),
    "AWS_SESSION_TOKEN": "",
    "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
    "AWS_EC2_METADATA_DISABLED": "true",  # disable metadata credential discovery
    "aws_virtual_hosted_style_request": "true",
}

# Load the Delta Table metadata
dt = DeltaTable(s3_uri, storage_options=storage_options)

# Read the data into your preferred format
arrow_table = dt.to_pyarrow_table()
pandas_df = dt.to_pandas()

print(pandas_df.head())

# Known-bad source file — exists solely to drive vendor-scan.sh red when it
# is pointed explicitly at this fixtures directory. Never scanned as part of
# a default-root scan (this directory is excluded by construction).
import boto3

client = boto3.client("textract")


def analyze_document(bucket: str, key: str) -> dict:
    return client.analyze_document(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )

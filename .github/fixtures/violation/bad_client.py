# Known-bad source file — exists solely to drive vendor-scan.sh red when it
# is pointed explicitly at this fixtures directory. Never scanned as part of
# a default-root scan (this directory is excluded by construction).
import boto3

client = boto3.client("textract")


def analyze_document(bucket: str, key: str) -> dict:
    return client.analyze_document(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )


# Second known-bad call site: AWS Transcribe. "transcribe" is matched only as a
# boto3-qualified client construction (the bare word is this project's own
# provenance verb), so this line is what proves that narrowing still catches the
# actual service. If vendor-scan.sh ever stops flagging this, the gate is broken.
transcribe_client = boto3.client("transcribe")


def start_transcription(uri: str) -> dict:
    return transcribe_client.start_transcription_job(
        TranscriptionJobName="job", Media={"MediaFileUri": uri}
    )

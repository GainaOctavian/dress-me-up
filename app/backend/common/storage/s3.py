"""S3 access for the API and the worker (SeaweedFS locally, any S3 in prod).

Two clients: `_internal` talks to S3 from inside the stack, `_public` only
*signs* URLs, with the endpoint the phone can reach (LAN IP locally).
Signing is local (no network call), so presigning lists is cheap.
"""
import os
from functools import lru_cache

import boto3
from botocore.config import Config

BUCKET = os.getenv("S3_BUCKET", "dress-me-up")
GET_URL_EXPIRES = 24 * 3600  # clients cache item lists; keep image URLs valid a day


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )


@lru_cache(maxsize=1)
def _internal():
    return _client(os.getenv("S3_ENDPOINT_URL", "http://localhost:8333"))


@lru_cache(maxsize=1)
def _public():
    return _client(
        os.getenv("S3_PUBLIC_ENDPOINT_URL")
        or os.getenv("S3_ENDPOINT_URL", "http://localhost:8333")
    )


def presigned_post(key: str, mime_type: str, max_bytes: int, expires: int = 600) -> dict:
    """URL + form fields for a direct browser/phone upload. S3 itself rejects
    files over max_bytes or with another content type."""
    return _public().generate_presigned_post(
        BUCKET,
        key,
        Fields={"Content-Type": mime_type},
        Conditions=[
            {"Content-Type": mime_type},
            ["content-length-range", 1, max_bytes],
        ],
        ExpiresIn=expires,
    )


def presigned_get(key: str) -> str:
    return _public().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=GET_URL_EXPIRES,
    )


def head(key: str):
    """Object metadata, or None if it doesn't exist."""
    try:
        return _internal().head_object(Bucket=BUCKET, Key=key)
    except _internal().exceptions.ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def get_bytes(key: str) -> bytes:
    return _internal().get_object(Bucket=BUCKET, Key=key)["Body"].read()


def put_bytes(key: str, data: bytes, mime_type: str) -> None:
    _internal().put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=mime_type)


def delete(key: str) -> None:
    _internal().delete_object(Bucket=BUCKET, Key=key)

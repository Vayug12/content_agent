"""Cloudflare R2 storage.

R2 yahan library nahi hai - sirf handoff buffer hai. Render async hota hai,
toh video ko kahin toh rukna padta hai jab tak user app kholke download na kare.
Lifecycle rule R2_RETENTION_DAYS ke baad file khud delete kar deta hai;
job row (title, date) SQLite me rehti hai taaki history dikhti rahe.
"""

import os
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from config import (
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_BUCKET, R2_PUBLIC_BASE_URL, R2_RETENTION_DAYS, R2_OBJECT_PREFIX
)
from utils.logger import log

# SigV4 presigned URLs 7 din se zyada valid nahi ho sakte - ye AWS ka hard limit hai
PRESIGN_MAX_SECONDS = 7 * 24 * 3600

LIFECYCLE_RULE_ID = "expire-generated-videos"


def is_configured() -> bool:
    return all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET])


def get_client():
    """R2 S3-compatible client. Region 'auto' hona zaroori hai."""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def presign_seconds() -> int:
    """Link kabhi file se zyada zinda na rahe - warna user ko 404 milega."""
    return min(R2_RETENTION_DAYS * 24 * 3600, PRESIGN_MAX_SECONDS)


def upload_video(local_path: str, key: str) -> dict:
    """Video R2 pe upload karo aur download URL return karo.

    App is URL se file device pe download karti hai, phir Android share sheet
    ko local file ka content:// URI deti hai. Ye URL kisi aur ke paas nahi jata.
    """
    if not is_configured():
        log("STORAGE", "R2 not configured - skipping upload")
        return {}

    if not os.path.exists(local_path):
        log("STORAGE", f"File not found: {local_path}")
        return {}

    try:
        client = get_client()
        size = os.path.getsize(local_path)

        client.upload_file(
            local_path, R2_BUCKET, key,
            ExtraArgs={"ContentType": "video/mp4"}
        )

        if R2_PUBLIC_BASE_URL:
            url = f"{R2_PUBLIC_BASE_URL}/{key}"
            expires_in = 0
        else:
            expires_in = presign_seconds()
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": R2_BUCKET, "Key": key},
                ExpiresIn=expires_in,
            )

        log("STORAGE", f"Uploaded to R2: {key} ({size // 1024}KB)")
        return {"url": url, "key": key, "size": size, "expires_in": expires_in}

    except (BotoCoreError, ClientError) as e:
        log("STORAGE", f"R2 upload failed: {str(e)}")
        return {}


def delete_video(key: str) -> bool:
    """User apni library se video delete kare toh R2 se turant hatao.

    Lifecycle rule waise bhi hata deta, par user ke delete ka matlab abhi hai.
    """
    if not is_configured() or not key:
        return False
    try:
        get_client().delete_object(Bucket=R2_BUCKET, Key=key)
        log("STORAGE", f"Deleted from R2: {key}")
        return True
    except (BotoCoreError, ClientError) as e:
        log("STORAGE", f"R2 delete failed: {str(e)}")
        return False


def apply_lifecycle_rule() -> bool:
    """Bucket pe expiry rule lagao. Idempotent hai - baar baar chala sakte ho.

    Do cheezein karta hai:
      1. R2_OBJECT_PREFIX ke objects R2_RETENTION_DAYS baad delete
      2. Adhoore multipart uploads 1 din baad clean (warna chupke se bill badhta hai)
    """
    if not is_configured():
        log("STORAGE", "R2 not configured - cannot apply lifecycle rule")
        return False

    try:
        get_client().put_bucket_lifecycle_configuration(
            Bucket=R2_BUCKET,
            LifecycleConfiguration={
                "Rules": [
                    {
                        "ID": LIFECYCLE_RULE_ID,
                        "Status": "Enabled",
                        "Filter": {"Prefix": R2_OBJECT_PREFIX},
                        "Expiration": {"Days": R2_RETENTION_DAYS},
                        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                    }
                ]
            },
        )
        log("STORAGE",
            f"Lifecycle rule applied: {R2_OBJECT_PREFIX}* expires after {R2_RETENTION_DAYS} days")
        return True

    except (BotoCoreError, ClientError) as e:
        log("STORAGE", f"Failed to apply lifecycle rule: {str(e)}")
        return False


def get_lifecycle_rule() -> list:
    """Rule sach me laga hai ya nahi - verify karne ke liye."""
    if not is_configured():
        return []
    try:
        result = get_client().get_bucket_lifecycle_configuration(Bucket=R2_BUCKET)
        return result.get("Rules", [])
    except (BotoCoreError, ClientError) as e:
        log("STORAGE", f"Could not read lifecycle rules: {str(e)}")
        return []

"""One-time R2 bucket setup.

Applies the lifecycle rule that expires generated videos, then prints back what
the bucket actually reports so you can confirm it took.

    python setup_r2.py

Safe to re-run - it overwrites the rule with the current R2_RETENTION_DAYS.
"""

import sys
from config import R2_BUCKET, R2_RETENTION_DAYS, R2_OBJECT_PREFIX, R2_PUBLIC_BASE_URL
from utils.storage import (
    is_configured, apply_lifecycle_rule, get_lifecycle_rule, presign_seconds
)


def main() -> int:
    if not is_configured():
        print("R2 is not configured. Fill in the R2_* values in .env first.")
        return 1

    print(f"Bucket:    {R2_BUCKET}")
    print(f"Prefix:    {R2_OBJECT_PREFIX}")
    print(f"Retention: {R2_RETENTION_DAYS} days")

    if R2_PUBLIC_BASE_URL:
        print(f"Links:     permanent, via {R2_PUBLIC_BASE_URL}")
    else:
        print(f"Links:     presigned, valid {presign_seconds() // 3600}h")
        if R2_RETENTION_DAYS * 24 * 3600 > presign_seconds():
            print("           NOTE: presigned URLs cap at 7 days (SigV4 limit), so links")
            print("           expire before the file does. Set R2_PUBLIC_BASE_URL if you")
            print("           want the full retention window to be reachable.")

    print()
    if not apply_lifecycle_rule():
        return 1

    rules = get_lifecycle_rule()
    if not rules:
        print("Rule applied but the bucket reported none back. Check R2 permissions.")
        return 1

    print("Bucket now reports:")
    for rule in rules:
        days = rule.get("Expiration", {}).get("Days", "?")
        prefix = rule.get("Filter", {}).get("Prefix", "")
        print(f"  [{rule.get('Status')}] {rule.get('ID')}: {prefix}* expires after {days} days")

    print()
    print("Existing objects can take up to 24h to be processed by a new rule.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

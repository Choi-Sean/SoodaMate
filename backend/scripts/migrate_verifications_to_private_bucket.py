"""Moves existing face-verification selfies / ID photos out of the public-read
bucket into the private one (settings.r2_private_bucket_name).

Run from the backend folder AFTER creating the private bucket (Cloudflare R2, no
public access) and setting R2_PRIVATE_BUCKET_NAME:

    python scripts/migrate_verifications_to_private_bucket.py            # dry run, changes nothing
    python scripts/migrate_verifications_to_private_bucket.py --execute  # copy, verify, then delete the public copy

Keys keep the same names, so no database row changes. Safe to re-run: objects
already in the private bucket are skipped, and a public copy is only deleted
after the private copy's size has been checked.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.services import storage_service  # noqa: E402


def main(execute: bool) -> int:
    private = settings.r2_private_bucket_name
    public = settings.r2_bucket_name
    if not private:
        print("R2_PRIVATE_BUCKET_NAME is not set - nothing to migrate to.")
        return 1
    if private == public:
        print("The private bucket is the same as the public one - refusing.")
        return 1
    client = storage_service._get_client()

    moved = skipped = failed = 0
    token = None
    while True:
        kwargs = {"Bucket": public, "Prefix": "verifications/"}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            key, size = obj["Key"], obj["Size"]
            try:
                try:
                    already = client.head_object(Bucket=private, Key=key)["ContentLength"] == size
                except Exception:  # noqa: BLE001 - not there yet
                    already = False
                if not already:
                    print(f"{'COPY  ' if execute else 'would copy'} {key} ({size} bytes)")
                    if execute:
                        client.copy_object(Bucket=private, Key=key, CopySource={"Bucket": public, "Key": key})
                        if client.head_object(Bucket=private, Key=key)["ContentLength"] != size:
                            raise RuntimeError("size mismatch after copy")
                else:
                    skipped += 1
                if execute:
                    client.delete_object(Bucket=public, Key=key)
                moved += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"FAILED {key}: {exc}")
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")

    print(f"\n{'moved' if execute else 'would move'}: {moved}  (already in private bucket: {skipped})  failed: {failed}")
    if not execute:
        print("Dry run - re-run with --execute to apply.")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    sys.exit(main(parser.parse_args().execute))

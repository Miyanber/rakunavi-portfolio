import boto3
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "docs/images/ をS3のdocs-images/に同期する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="実際にアップロードせず確認のみ",
        )

    def handle(self, *args, **options):
        images_dir = Path(settings.BASE_DIR) / "docs" / "images"
        if not images_dir.exists():
            self.stderr.write(f"{images_dir} が見つかりません")
            return

        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_S3_REGION_NAME"),
        )
        bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME")

        for file_path in images_dir.iterdir():
            if not file_path.is_file():
                continue
            s3_key = f"docs-images/{file_path.name}"

            if options["dry_run"]:
                self.stdout.write(f"[dry-run] {file_path.name} → s3://{bucket}/{s3_key}")
                continue

            s3.upload_file(
                str(file_path),
                bucket,
                s3_key,
                ExtraArgs={
                    "ContentType": self._content_type(file_path.suffix),
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )
            self.stdout.write(self.style.SUCCESS(f"アップロード完了: {file_path.name}"))

    def _content_type(self, suffix: str) -> str:
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }.get(suffix.lower(), "application/octet-stream")

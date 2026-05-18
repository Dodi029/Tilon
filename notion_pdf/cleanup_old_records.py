import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import delete_expired_records, init_db


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "output"
UPLOAD_DIR = ROOT_DIR / "uploads"
LOG_DIR = ROOT_DIR / "logs"
LOG_PATH = LOG_DIR / "cleanup.log"
DEFAULT_RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "7"))
MANAGED_SUFFIXES = {".html", ".htm", ".zip", ".pdf", ".txt", ".png"}


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(f"{stamp} {message}\n")


def remove_file(path_value: str | None) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    try:
        if path.exists() and path.is_file():
            path.unlink()
            log(f"deleted file path={path}")
            return True
    except Exception as exc:
        log(f"failed delete file path={path} error={exc}")
    return False


def cleanup_output_files(retention_days: int, dry_run: bool = False) -> int:
    threshold = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = 0
    for directory in (OUTPUT_DIR, UPLOAD_DIR):
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() not in MANAGED_SUFFIXES:
                continue
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if modified > threshold:
                    continue
                if dry_run:
                    log(f"dry-run delete old output path={path}")
                else:
                    path.unlink()
                    log(f"deleted old output path={path}")
                deleted += 1
            except Exception as exc:
                log(f"failed delete old output path={path} error={exc}")
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean expired notion_pdf records and generated files.")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    init_db()
    expired_rows = delete_expired_records() if not args.dry_run else []
    deleted_from_db_paths = 0
    if args.dry_run:
        log("dry-run skip DB deletion")
    for row in expired_rows:
        deleted_from_db_paths += int(remove_file(row.get("input_file_path")))
        deleted_from_db_paths += int(remove_file(row.get("output_pdf_path")))
        deleted_from_db_paths += int(remove_file(row.get("output_txt_path")))
        deleted_from_db_paths += int(remove_file(row.get("output_png_path")))
    deleted_old_files = cleanup_output_files(args.retention_days, dry_run=args.dry_run)
    log(
        "cleanup complete "
        f"expired_records={len(expired_rows)} "
        f"record_files_deleted={deleted_from_db_paths} "
        f"old_files_deleted={deleted_old_files} "
        f"retention_days={args.retention_days} dry_run={args.dry_run}"
    )
    print(f"EXPIRED_RECORDS={len(expired_rows)}")
    print(f"RECORD_FILES_DELETED={deleted_from_db_paths}")
    print(f"OLD_FILES_DELETED={deleted_old_files}")
    print(f"LOG={LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

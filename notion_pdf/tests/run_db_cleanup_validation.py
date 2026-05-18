import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cleanup_old_records import cleanup_output_files, remove_file
from db import DB_PATH, delete_expired_records, get_connection, init_db, record_conversion, utc_now


OUTPUT_DIR = ROOT / "output"
UPLOADS_DIR = ROOT / "uploads"


def count_rows(status: str) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM conversions WHERE status = ?", (status,)).fetchone()
    return int(row["count"])


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    UPLOADS_DIR.mkdir(exist_ok=True)
    init_db()

    now = utc_now()
    expired_input = UPLOADS_DIR / "cleanup_validation_expired.html"
    expired_pdf = OUTPUT_DIR / "cleanup_validation_expired.pdf"
    expired_txt = OUTPUT_DIR / "cleanup_validation_expired.txt"
    expired_png = OUTPUT_DIR / "cleanup_validation_expired.png"
    old_png = OUTPUT_DIR / "cleanup_validation_old.png"
    for path in (expired_input, expired_pdf, expired_txt, expired_png, old_png):
        path.write_bytes(b"cleanup validation")
        old_time = (now - timedelta(days=8)).timestamp()
        os.utime(path, (old_time, old_time))

    expired_id = record_conversion(
        source_type="html_upload",
        original_filename="cleanup-validation.html",
        input_original_name="cleanup-validation.html",
        input_file_path=str(expired_input),
        input_file_size=expired_input.stat().st_size,
        output_pdf_path=str(expired_pdf),
        output_txt_path=str(expired_txt),
        output_png_path=str(expired_png),
        status="success",
        file_size=expired_pdf.stat().st_size,
        expires_at=(now - timedelta(seconds=1)).isoformat(timespec="seconds"),
    )
    failed_id = record_conversion(
        source_type="url",
        source_url="https://invalid.example.test",
        status="failed",
        error_message="synthetic validation failure",
        expires_at=(now + timedelta(days=7)).isoformat(timespec="seconds"),
    )

    expired_rows = delete_expired_records()
    deleted_record_files = 0
    for row in expired_rows:
        deleted_record_files += int(remove_file(row.get("input_file_path")))
        deleted_record_files += int(remove_file(row.get("output_pdf_path")))
        deleted_record_files += int(remove_file(row.get("output_txt_path")))
        deleted_record_files += int(remove_file(row.get("output_png_path")))
    deleted_old_files = cleanup_output_files(retention_days=7)

    if expired_input.exists() or expired_pdf.exists() or expired_txt.exists() or expired_png.exists() or old_png.exists():
        raise AssertionError("Expected expired output files to be deleted")

    with get_connection() as conn:
        expired_still_exists = conn.execute("SELECT COUNT(*) AS count FROM conversions WHERE id = ?", (expired_id,)).fetchone()
        failed_still_exists = conn.execute("SELECT COUNT(*) AS count FROM conversions WHERE id = ?", (failed_id,)).fetchone()
    if int(expired_still_exists["count"]) != 0:
        raise AssertionError("Expired DB record was not deleted")
    if int(failed_still_exists["count"]) != 1:
        raise AssertionError("Non-expired failed DB record was not preserved")

    print(f"DB_PATH={DB_PATH}")
    print(f"SUCCESS_RECORDS={count_rows('success')}")
    print(f"FAILED_RECORDS={count_rows('failed')}")
    print(f"EXPIRED_RECORDS_DELETED={len(expired_rows)}")
    print(f"RECORD_FILES_DELETED={deleted_record_files}")
    print(f"OLD_FILES_DELETED={deleted_old_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

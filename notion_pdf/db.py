import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = ROOT_DIR / "instance"
DB_PATH = INSTANCE_DIR / "notion_pdf.db"
DEFAULT_RETENTION_DAYS = 7


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def default_expires_at(days: int = DEFAULT_RETENTION_DAYS) -> str:
    return isoformat(utc_now() + timedelta(days=days))


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                original_filename TEXT,
                input_file_path TEXT,
                input_file_size INTEGER,
                input_original_name TEXT,
                output_pdf_path TEXT,
                output_txt_path TEXT,
                output_png_path TEXT,
                page_width INTEGER,
                margin INTEGER,
                quality_scale INTEGER,
                text_layer_mode TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                file_size INTEGER,
                client_ip TEXT,
                expires_at TEXT NOT NULL
            )
            """
        )
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(conversions)").fetchall()
        }
        migrations = {
            "input_file_path": "ALTER TABLE conversions ADD COLUMN input_file_path TEXT",
            "input_file_size": "ALTER TABLE conversions ADD COLUMN input_file_size INTEGER",
            "input_original_name": "ALTER TABLE conversions ADD COLUMN input_original_name TEXT",
            "output_png_path": "ALTER TABLE conversions ADD COLUMN output_png_path TEXT",
        }
        for column, sql in migrations.items():
            if column not in existing_columns:
                conn.execute(sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversions_created_at ON conversions(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversions_expires_at ON conversions(expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversions_status ON conversions(status)")


def record_conversion(**values) -> int | None:
    init_db()
    now = isoformat(utc_now())
    data = {
        "created_at": values.get("created_at") or now,
        "source_type": values.get("source_type") or "",
        "source_url": values.get("source_url"),
        "original_filename": values.get("original_filename"),
        "input_file_path": values.get("input_file_path"),
        "input_file_size": values.get("input_file_size"),
        "input_original_name": values.get("input_original_name"),
        "output_pdf_path": values.get("output_pdf_path"),
        "output_txt_path": values.get("output_txt_path"),
        "output_png_path": values.get("output_png_path"),
        "page_width": values.get("page_width"),
        "margin": values.get("margin"),
        "quality_scale": values.get("quality_scale"),
        "text_layer_mode": values.get("text_layer_mode"),
        "status": values.get("status") or "failed",
        "error_message": values.get("error_message"),
        "file_size": values.get("file_size"),
        "client_ip": values.get("client_ip"),
        "expires_at": values.get("expires_at") or default_expires_at(),
    }
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO conversions ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        return int(cursor.lastrowid)


def list_recent_conversions(limit: int = 50) -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM conversions
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversion(conversion_id: int) -> dict | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversions WHERE id = ?",
            (conversion_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_expired_records(now: datetime | None = None) -> list[dict]:
    init_db()
    threshold = isoformat(now or utc_now())
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM conversions WHERE expires_at <= ? ORDER BY expires_at ASC",
            (threshold,),
        ).fetchall()
        conn.execute("DELETE FROM conversions WHERE expires_at <= ?", (threshold,))
    return [dict(row) for row in rows]

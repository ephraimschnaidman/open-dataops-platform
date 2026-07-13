from __future__ import annotations

import csv
import logging
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA_DIR = REPO_ROOT / "domains" / "ecommerce" / "sample_data"
DDL_PATH = REPO_ROOT / "platform" / "warehouse" / "sql" / "create_raw_ecommerce_tables.sql"
TABLE_LOADS = [("customers.csv", "customers"), ("products.csv", "products"),
               ("orders.csv", "orders"), ("order_items.csv", "order_items"),
               ("payments.csv", "payments"), ("web_events.csv", "web_events")]

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def get_connection_params() -> dict[str, str]:
    load_dotenv(REPO_ROOT / ".env")
    return {"host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5433"),
            "dbname": os.getenv("POSTGRES_DB", "dataops"),
            "user": os.getenv("POSTGRES_USER", "dataops"),
            "password": os.getenv("POSTGRES_PASSWORD", "")}


def count_csv_rows(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        return max(sum(1 for _ in csv_file) - 1, 0)


def create_raw_tables(conn: psycopg.Connection) -> None:
    logger.info("Creating raw ecommerce tables if they do not exist")
    conn.execute(DDL_PATH.read_text(encoding="utf-8"))


def truncate_raw_tables(conn: psycopg.Connection) -> None:
    identifiers = [sql.Identifier("raw", table) for _, table in TABLE_LOADS]
    logger.info("Truncating raw ecommerce tables for deterministic bootstrap load")
    conn.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.SQL(", ").join(identifiers)))


def load_csv(conn: psycopg.Connection, csv_path: Path, table_name: str) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing source CSV: {csv_path}")
    statement = sql.SQL("COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)").format(
        sql.Identifier("raw", table_name))
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file, conn.cursor() as cur:
        with cur.copy(statement) as copy:
            while data := csv_file.read(8192):
                copy.write(data)
    return count_csv_rows(csv_path)


def bootstrap_raw_data() -> None:
    params = get_connection_params()
    logger.info("Starting raw ecommerce bootstrap", extra={"database": params["dbname"]})
    with psycopg.connect(**params) as conn:
        create_raw_tables(conn)
        truncate_raw_tables(conn)
        for csv_name, table_name in TABLE_LOADS:
            rows = load_csv(conn, SAMPLE_DATA_DIR / csv_name, table_name)
            logger.info("Loaded raw table", extra={"table": table_name, "rows": rows})
        conn.commit()
    logger.info("Raw ecommerce bootstrap complete")


def main() -> int:
    configure_logging()
    try:
        bootstrap_raw_data()
    except Exception:
        logger.exception("Raw ecommerce bootstrap failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

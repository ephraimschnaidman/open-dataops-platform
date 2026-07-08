from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_DIR = REPO_ROOT / "domains" / "ecommerce" / "sample_data"
DDL_PATH = REPO_ROOT / "platform" / "warehouse" / "sql" / "create_raw_ecommerce_tables.sql"

TABLE_LOADS = [
    ("customers.csv", "customers"),
    ("products.csv", "products"),
    ("orders.csv", "orders"),
    ("order_items.csv", "order_items"),
    ("payments.csv", "payments"),
    ("web_events.csv", "web_events"),
]


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def get_connection_params() -> dict[str, str]:
    load_dotenv(REPO_ROOT / ".env")

    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5433"),
        "dbname": os.getenv("POSTGRES_DB", "dataops"),
        "user": os.getenv("POSTGRES_USER", "dataops"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }


def count_csv_rows(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        return max(sum(1 for _ in csv_file) - 1, 0)


def create_raw_tables(conn: psycopg.Connection) -> None:
    logging.info("Creating raw ecommerce tables if they do not exist")
    conn.execute(DDL_PATH.read_text(encoding="utf-8"))


def truncate_raw_tables(conn: psycopg.Connection) -> None:
    table_identifiers = [
        sql.Identifier("raw", table_name) for _, table_name in TABLE_LOADS
    ]
    truncate_statement = sql.SQL("TRUNCATE TABLE {}").format(
        sql.SQL(", ").join(table_identifiers)
    )

    logging.info("Truncating raw ecommerce tables for deterministic bootstrap load")
    conn.execute(truncate_statement)


def load_csv(conn: psycopg.Connection, csv_path: Path, table_name: str) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing source CSV: {csv_path}")

    copy_statement = sql.SQL(
        "COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    ).format(sql.Identifier("raw", table_name))

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        with conn.cursor() as cur:
            with cur.copy(copy_statement) as copy:
                while data := csv_file.read(8192):
                    copy.write(data)

    return count_csv_rows(csv_path)


def bootstrap_raw_ecommerce_data() -> None:
    configure_logging()
    connection_params = get_connection_params()

    logging.info(
        "Starting local raw ecommerce bootstrap full refresh from sample CSV files"
    )
    logging.info(
        "Connecting to Postgres at %s:%s/%s",
        connection_params["host"],
        connection_params["port"],
        connection_params["dbname"],
    )

    with psycopg.connect(**connection_params) as conn:
        create_raw_tables(conn)
        truncate_raw_tables(conn)

        for csv_file_name, table_name in TABLE_LOADS:
            csv_path = SAMPLE_DATA_DIR / csv_file_name
            loaded_rows = load_csv(conn, csv_path, table_name)
            logging.info("Loaded %s rows into raw.%s", loaded_rows, table_name)

        conn.commit()

    logging.info("Raw ecommerce bootstrap full refresh complete")


def main() -> None:
    bootstrap_raw_ecommerce_data()


if __name__ == "__main__":
    main()

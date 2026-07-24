import sys
import tempfile
import unittest
from pathlib import Path

from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "jobs"))

from bootstrap_raw_data import load_csv  # noqa: E402


class FakeCopy:
    def __init__(self, connection, statement):
        self.connection = connection
        self.statement = statement

    def __enter__(self):
        statement = self.statement.as_string()
        self.connection.copy_statement = statement
        for column in self.connection.unknown_columns:
            if f'"{column}"' in statement:
                raise RuntimeError(
                    f'column "{column}" of relation "customers" does not exist'
                )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def write(self, data):
        self.connection.copied_data += data


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def copy(self, statement):
        return FakeCopy(self.connection, statement)


class FakeConnection:
    def __init__(self, unknown_columns=()):
        self.unknown_columns = set(unknown_columns)
        self.copy_statement = None
        self.copied_data = ""

    def cursor(self):
        return FakeCursor(self)


class BootstrapRawDataTests(unittest.TestCase):
    def write_csv(self, contents):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "customers.csv"
        path.write_text(contents, encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_copy_uses_explicit_header_columns(self):
        connection = FakeConnection()
        path = self.write_csv("customer_id,email\ncustomer-1,one@example.com\n")

        rows = load_csv(connection, path, "customers")

        self.assertEqual(rows, 1)
        self.assertEqual(
            connection.copy_statement,
            'COPY "raw"."customers" ("customer_id", "email") '
            "FROM STDIN WITH (FORMAT CSV, HEADER TRUE)",
        )

    def test_extra_database_columns_do_not_break_loading(self):
        connection = FakeConnection()
        path = self.write_csv("customer_id,email\ncustomer-1,one@example.com\n")

        rows = load_csv(connection, path, "customers")

        self.assertEqual(rows, 1)
        self.assertNotIn("schema_change_test", connection.copy_statement)

    def test_missing_csv_header_is_rejected(self):
        for contents in ("", "\n"):
            with self.subTest(contents=contents):
                with self.assertRaisesRegex(ValueError, "Missing CSV header"):
                    load_csv(FakeConnection(), self.write_csv(contents), "customers")

    def test_duplicate_csv_header_columns_are_rejected(self):
        path = self.write_csv("customer_id,email,email\ncustomer-1,one@example.com,other\n")

        with self.assertRaisesRegex(ValueError, "duplicate column names.*'email'"):
            load_csv(FakeConnection(), path, "customers")

    def test_csv_column_missing_from_target_table_fails_clearly(self):
        path = self.write_csv("customer_id,unknown_column\ncustomer-1,value\n")

        with self.assertRaisesRegex(
            RuntimeError,
            'column "unknown_column" of relation "customers" does not exist',
        ):
            load_csv(
                FakeConnection(unknown_columns={"unknown_column"}),
                path,
                "customers",
            )

    def test_empty_csv_header_column_is_rejected(self):
        path = self.write_csv("customer_id, \ncustomer-1,value\n")

        with self.assertRaisesRegex(ValueError, "empty column name"):
            load_csv(FakeConnection(), path, "customers")

    def test_missing_file_behavior_is_preserved(self):
        path = Path(tempfile.gettempdir()) / "missing-bootstrap-source.csv"

        with self.assertRaisesRegex(FileNotFoundError, "Missing source CSV"):
            load_csv(FakeConnection(), path, "customers")


if __name__ == "__main__":
    unittest.main()

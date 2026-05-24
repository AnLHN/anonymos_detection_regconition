import json
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[2]
EXPORT_PATH = ROOT / "data" / "exports" / "postgres_20260521T080719Z.json"

DSN = "host=localhost port=7001 dbname=face_db user=face_user password=face_password"

TYPE_MAP = {
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "boolean": "BOOLEAN",
    "text": "TEXT",
    "character varying": "TEXT",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMPTZ",
    "date": "DATE",
    "numeric": "NUMERIC",
    "double precision": "DOUBLE PRECISION",
    "real": "REAL",
    "json": "JSONB",
    "jsonb": "JSONB",
}


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def column_type(column: dict[str, Any]) -> str:
    data_type = column["data_type"]
    return TYPE_MAP.get(data_type, "TEXT")


def create_table_sql(table: dict[str, Any]) -> str:
    columns = []
    primary_keys = set(table.get("primary_key", []))

    for column in table["columns"]:
        name = quote_ident(column["column_name"])
        sql_type = column_type(column)
        nullable = "" if column["is_nullable"] == "YES" or column["column_name"] in primary_keys else " NOT NULL"
        columns.append(f"{name} {sql_type}{nullable}")

    if primary_keys:
        keys = ", ".join(quote_ident(key) for key in primary_keys)
        columns.append(f"PRIMARY KEY ({keys})")

    schema = quote_ident(table["schema"])
    name = quote_ident(table["name"])
    return f"CREATE SCHEMA IF NOT EXISTS {schema}; CREATE TABLE IF NOT EXISTS {schema}.{name} ({', '.join(columns)});"


def insert_rows(cur: psycopg.Cursor, table: dict[str, Any]) -> None:
    rows = table.get("rows", [])
    if not rows:
        return

    schema = quote_ident(table["schema"])
    name = quote_ident(table["name"])
    column_names = [column["column_name"] for column in table["columns"]]
    quoted_columns = ", ".join(quote_ident(column) for column in column_names)
    placeholders = ", ".join(["%s"] * len(column_names))
    primary_keys = table.get("primary_key", [])
    conflict = ""
    if primary_keys:
        conflict_keys = ", ".join(quote_ident(key) for key in primary_keys)
        conflict = f" ON CONFLICT ({conflict_keys}) DO NOTHING"

    sql = f"INSERT INTO {schema}.{name} ({quoted_columns}) VALUES ({placeholders}){conflict}"
    values = [[row.get(column) for column in column_names] for row in rows]
    cur.executemany(sql, values)


def main() -> None:
    export = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            for table in export["tables"]:
                cur.execute(create_table_sql(table))
            for table in export["tables"]:
                insert_rows(cur, table)
        conn.commit()

    print(f"Imported Postgres export: {EXPORT_PATH}")


if __name__ == "__main__":
    main()

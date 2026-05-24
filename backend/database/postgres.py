from typing import Any

import psycopg
from psycopg.rows import dict_row

from backend.config import POSTGRES_DSN


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with psycopg.connect(POSTGRES_DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with psycopg.connect(POSTGRES_DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> None:
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()

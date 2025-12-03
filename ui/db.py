import os
from typing import Dict, List, Tuple

import pandas as pd
import psycopg
from psycopg import sql
from psycopg.rows import dict_row


REFRESH_MS = int(os.getenv("NGMI_UI_REFRESH_MS", "5000"))
ROW_LIMIT = int(os.getenv("NGMI_UI_ROW_LIMIT", "100"))


def get_conn():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "ngmidbms"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
        port=os.getenv("DB_PORT", "5432"),
        row_factory=dict_row,
        autocommit=True,
    )


def fetch_all(query, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            try:
                return cur.fetchall()
            except Exception:
                return []


def fetch_statement(statement: sql.SQL, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(statement, params)
            try:
                return cur.fetchall()
            except Exception:
                return []


def fetch_schema() -> Tuple[List[str], Dict[str, List[Dict]], List[Dict]]:
    tables = [
        row["table_name"]
        for row in fetch_all(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    ]

    columns: Dict[str, List[Dict]] = {}
    if tables:
        cols = fetch_all(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
        for col in cols:
            columns.setdefault(col["table_name"], []).append(col)

    fks = fetch_all(
        """
        SELECT tc.table_name,
               kcu.column_name,
               ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        """
    )

    return tables, columns, fks


def fetch_table_counts(tables: List[str]) -> List[Dict]:
    counts = []
    for table in tables:
        stmt = sql.SQL("SELECT COUNT(*) AS count FROM {}").format(sql.Identifier(table))
        rows = fetch_statement(stmt)
        count = rows[0]["count"] if rows else 0
        counts.append({"table": table, "count": count})
    return counts


def fetch_table_preview(table: str, limit: int) -> pd.DataFrame:
    stmt = (
        sql.SQL("SELECT * FROM {} ORDER BY 1 DESC LIMIT %s").format(sql.Identifier(table))
    )
    rows = fetch_statement(stmt, (limit,))
    return pd.DataFrame(rows)


def fetch_activity(limit: int = 20) -> List[Dict]:
    return fetch_all(
        """
        SELECT * FROM (
            SELECT 'users' AS table_name, created_at AS ts, email AS summary FROM users
            UNION ALL
            SELECT 'resumes', uploaded_at, file_name FROM resumes
            UNION ALL
            SELECT 'applications', applied_at, CONCAT('job ', job_id, ' resume ', resume_id) FROM applications
            UNION ALL
            SELECT 'ngmiscores', generated_at, CONCAT('score ', ngmi_score) FROM ngmiscores
        ) AS combined
        WHERE ts IS NOT NULL
        ORDER BY ts DESC
        LIMIT %s
        """,
        (limit,),
    )

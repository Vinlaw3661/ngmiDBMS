from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from . import db

app = FastAPI(title="ngmiDBMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/schema")
def api_schema():
    tables, columns, fks = db.fetch_schema()
    return {"tables": tables, "columns": columns, "fks": fks}


@app.get("/api/counts")
def api_counts():
    tables, _, _ = db.fetch_schema()
    counts = db.fetch_table_counts(tables) if tables else []
    return counts


@app.get("/api/preview")
def api_preview(table: str = Query(...), limit: Optional[int] = Query(None)):
    if not table:
        return {"columns": [], "rows": []}
    limit_val = int(limit) if limit else db.ROW_LIMIT
    df = db.fetch_table_preview(table, limit_val)
    cols = list(df.columns) if not df.empty else []
    rows = df.to_dict("records") if not df.empty else []
    return {"columns": cols, "rows": rows}


@app.get("/api/activity")
def api_activity(limit: Optional[int] = Query(20)):
    limit_val = int(limit) if limit else 20
    act = db.fetch_activity(limit_val)
    return act

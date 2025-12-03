import os
from typing import Dict, List, Tuple
import dash
import dash_cytoscape as cyto
from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update
from flask import jsonify, request
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


def build_schema_elements(tables: List[str], columns: Dict[str, List[Dict]], fks: List[Dict]):
    elements = []
    for table in tables:
        col_lines = columns.get(table, [])
        display_cols = "\n".join(
            f"- {c['column_name']} ({c['data_type']})" for c in col_lines[:8]
        )
        if len(col_lines) > 8:
            display_cols += "\n…"
        label = f"{table}\n{display_cols}".strip()
        elements.append({"data": {"id": table, "label": label}, "classes": "table"})

    for fk in fks:
        elements.append(
            {
                "data": {
                    "source": fk["table_name"],
                    "target": fk["foreign_table_name"],
                    "label": f"{fk['column_name']} → {fk['foreign_column_name']}",
                },
                "classes": "fk",
            }
        )
    return elements


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
        sql.SQL("SELECT * FROM {} ORDER BY 1 DESC LIMIT %s").format(
            sql.Identifier(table)
        )
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


BACKGROUND = "#0b1320"
PANEL_BG = "#131b2c"
CARD_BG = "#192235"
PRIMARY = "#3c82f6"
TEXT = "#e9ecef"
MUTED = "#98a3b8"

app: Dash = dash.Dash(__name__)
server = app.server

cyto_stylesheet = [
    {
        "selector": "node",
        "style": {
            "content": "data(label)",
            "text-wrap": "wrap",
            "text-max-width": 220,
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "12px",
            "background-color": PRIMARY,
            "color": TEXT,
            "shape": "ellipse",
            "padding": "6px",
            "width": "label",
            "height": "label",
            "min-width": "180px",
            "min-height": "130px",
            "border-width": 2,
            "border-color": "#2a5dcf",
            "box-shadow": "0 8px 18px rgba(0,0,0,0.35)",
        },
    },
    {
        "selector": ".fk",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "label": "data(label)",
            "font-size": "10px",
            "line-color": "#6ee7b7",
            "target-arrow-color": "#6ee7b7",
            "width": 3,
            "target-arrow-width": 10,
            "color": TEXT,
        },
    },
]

app.layout = html.Div(
    style={
        "backgroundColor": BACKGROUND,
        "color": TEXT,
        "minHeight": "100vh",
        "padding": "18px",
        "fontFamily": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    children=[
        html.Div(
            style={
                "position": "sticky",
                "top": 0,
                "zIndex": 100,
                "backgroundColor": BACKGROUND,
                "padding": "12px 12px 16px",
                "borderBottom": "1px solid rgba(255,255,255,0.06)",
            },
            children=[
                html.Div(
                    [
                        html.H1("ngmiDBMS Dashboard", style={"marginBottom": "4px"}),
                        html.P(
                            "Schema graph, table previews, and live-ish activity from Postgres.",
                            style={"color": MUTED, "marginTop": "0"},
                        ),
                    ]
                ),
                html.Div(
                    className="controls",
                    children=[
                        html.Div(
                            [
                                html.Div("Table", style={"color": MUTED, "fontSize": "12px"}),
                                dcc.Dropdown(
                                    id="table-dropdown",
                                    placeholder="Select a table",
                                    style={"color": "#000", "backgroundColor": "#f8f9fa"},
                                ),
                            ],
                            style={"flex": "1", "minWidth": "200px"},
                        ),
                        html.Div(
                            [
                                html.Div("Row limit", style={"color": MUTED, "fontSize": "12px"}),
                                dcc.Slider(
                                    id="row-limit",
                                    min=20,
                                    max=200,
                                    step=10,
                                    value=ROW_LIMIT,
                                    marks=None,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                            ],
                            style={"flex": "2", "minWidth": "250px"},
                        ),
                        html.Div(
                            [
                                html.Button(
                                    "Reset",
                                    id="reset-filters",
                                    n_clicks=0,
                                    style={
                                        "marginTop": "20px",
                                        "padding": "8px 14px",
                                        "backgroundColor": PRIMARY,
                                        "color": TEXT,
                                        "border": "none",
                                        "borderRadius": "8px",
                                        "cursor": "pointer",
                                    },
                                )
                            ],
                            style={"display": "flex", "alignItems": "flex-end"},
                        ),
                    ],
                    style={"display": "flex", "gap": "16px", "alignItems": "flex-end"},
                ),
            ],
        ),
        dcc.Interval(id="refresh-interval", interval=REFRESH_MS, n_intervals=0),
        html.Div(
            style={
                "display": "flex",
                "gap": "16px",
                "alignItems": "flex-start",
                "marginTop": "16px",
                "flexWrap": "wrap",
            },
            children=[
                html.Div(
                    style={"minWidth": 0, "overflowX": "auto", "flex": 3},
                    children=[
                        cyto.Cytoscape(
                            id="schema-graph",
                            layout={"name": "cose"},
                            style={
                                "height": "520px",
                                "width": "100%",
                                "minWidth": 0,
                                "border": "1px solid #23304a",
                                "backgroundColor": PANEL_BG,
                            },
                            elements=[],
                            stylesheet=cyto_stylesheet,
                        )
                    ],
                ),
                html.Div(
                    id="table-stats",
                    style={
                        "flex": 1,
                        "minWidth": "260px",
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(140px, 1fr))",
                        "gap": "8px",
                    },
                ),
            ],
        ),
        html.Div(
            []
        ),
        html.H3("Table Preview"),
        html.Div(
            [
                html.Div(id="table-preview-caption", style={"color": MUTED, "marginBottom": "6px"}),
                dcc.Loading(
                    type="circle",
                    children=[
                        dash_table.DataTable(
                            id="table-preview",
                            page_size=10,
                            sort_action="native",
                            filter_action="native",
                            style_table={
                                "overflowX": "auto",
                                "overflowY": "auto",
                                "maxHeight": "360px",
                                "backgroundColor": PANEL_BG,
                                "border": f"1px solid {PANEL_BG}",
                            },
                            style_cell={
                                "textAlign": "left",
                                "fontSize": "12px",
                                "backgroundColor": PANEL_BG,
                                "color": TEXT,
                                "border": "1px solid #23304a",
                            },
                            style_header={
                                "backgroundColor": "#1f2c45",
                                "color": TEXT,
                                "fontWeight": "bold",
                                "border": "1px solid #23304a",
                            },
                        )
                    ],
                ),
                html.Div(id="table-preview-empty", style={"marginTop": "8px", "color": MUTED}),
            ]
        ),
        html.H3("Recent Activity"),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Log", style={"fontWeight": "bold"}),
                    ],
                    style={"marginBottom": "6px"},
                ),
                html.Div(
                    id="activity-feed",
                    style={
                        "backgroundColor": PANEL_BG,
                        "border": "1px solid #23304a",
                        "borderRadius": "10px",
                        "padding": "12px",
                        "maxHeight": "280px",
                        "overflowY": "auto",
                        "fontFamily": "SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        "fontSize": "12px",
                    },
                ),
            ]
        ),
    ],
)


@app.callback(
    Output("schema-graph", "elements"),
    Output("table-dropdown", "options"),
    Output("table-dropdown", "value"),
    Output("table-stats", "children"),
    Output("activity-feed", "children"),
    Input("refresh-interval", "n_intervals"),
    Input("reset-filters", "n_clicks"),
    State("table-dropdown", "value"),
)
def refresh_dashboard(n_intervals, reset_clicks, current_table):
    tables, columns, fks = fetch_schema()
    if not tables:
        return [], [], None, "No tables found.", "No activity."

    trigger = dash.callback_context.triggered[0]["prop_id"].split(".")[0] if dash.callback_context.triggered else None
    reset_requested = trigger == "reset-filters"

    elements = build_schema_elements(tables, columns, fks)
    options = [{"label": t, "value": t} for t in tables]
    table_value = tables[0] if reset_requested else (current_table if current_table in tables else tables[0])

    counts = fetch_table_counts(tables)
    stats_cards = [
        html.Div(
            [
                html.Div(table["table"], style={"fontWeight": "bold"}),
                html.Div(f"{table['count']} rows", style={"color": MUTED}),
            ],
            style={
                "border": "1px solid #23304a",
                "borderRadius": "10px",
                "padding": "10px",
                "background": CARD_BG,
                "boxShadow": "0 6px 16px rgba(0,0,0,0.25)",
            },
        )
        for table in counts
    ]

    activity = fetch_activity()
    if activity:
        activity_nodes = [
            html.Div(
                f"[{row['ts']}] {row['table_name']}: {row['summary']}",
                style={"color": TEXT, "marginBottom": "4px"},
            )
            for row in activity
        ]
    else:
        activity_nodes = html.Div("No recent activity. Run a command or refresh.", style={"color": MUTED})

    if trigger == "refresh-interval" and current_table in tables and not reset_requested:
        return no_update, no_update, table_value, stats_cards, activity_nodes

    return elements, options, table_value, stats_cards, activity_nodes


@app.callback(
    Output("table-preview", "data"),
    Output("table-preview", "columns"),
    Output("table-preview-caption", "children"),
    Output("table-preview-empty", "children"),
    Input("table-dropdown", "value"),
    Input("row-limit", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_table_preview(table, row_limit, _):
    if not table:
        return [], [], "Select a table to preview rows.", ""

    df = fetch_table_preview(table, row_limit or ROW_LIMIT)
    columns = [{"name": col, "id": col} for col in df.columns]
    caption = f"Showing up to {row_limit or ROW_LIMIT} rows from `{table}` ({len(df)} returned)."
    empty_msg = ""
    if df.empty:
        empty_msg = "No rows returned. Try inserting data or increasing the row limit."
    return df.to_dict("records"), columns, caption, empty_msg


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=int(os.getenv("PORT", "8050")), debug=True)

"""Spreadsheet tools — CSV/XLSX read, query with pandas, summarize."""
from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool


@tool
def read_csv(path: str, max_rows: int = 50) -> str:
    """Read a CSV. Returns header + first N rows + shape."""
    try:
        import pandas as pd
    except ImportError:
        return "[error] pip install pandas"
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    try:
        df = pd.read_csv(p)
    except Exception as e:
        return f"[error] {e}"
    return (
        f"shape: {df.shape}\ndtypes:\n{df.dtypes.to_string()}\n\n"
        f"first {max_rows}:\n{df.head(max_rows).to_string()}"
    )


@tool
def read_xlsx(path: str, sheet: str = "", max_rows: int = 50) -> str:
    """Read an Excel sheet. sheet: name (empty = first)."""
    try:
        import pandas as pd
    except ImportError:
        return "[error] pip install pandas openpyxl"
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    try:
        df = pd.read_excel(p, sheet_name=sheet or 0)
    except Exception as e:
        return f"[error] {e}"
    return (
        f"shape: {df.shape}\ndtypes:\n{df.dtypes.to_string()}\n\n"
        f"first {max_rows}:\n{df.head(max_rows).to_string()}"
    )


@tool
def csv_query(path: str, pandas_expression: str) -> str:
    """Run a pandas expression on a CSV. df is the loaded DataFrame.
    Examples: "df.groupby('city')['amount'].sum()" or "df[df.amount > 100].head()"."""
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        return "[error] pip install pandas"
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    try:
        df = pd.read_csv(p)
        result = eval(
            pandas_expression,
            {"__builtins__": {}},
            {"df": df, "pd": pd, "np": np},
        )
        return str(result)[:5000]
    except Exception as e:
        return f"[error] {e}"


@tool
def csv_describe(path: str) -> str:
    """Statistical summary of a CSV (mean/std/percentiles per numeric column)."""
    try:
        import pandas as pd
    except ImportError:
        return "[error] pip install pandas"
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    try:
        df = pd.read_csv(p)
        return df.describe(include="all").to_string()
    except Exception as e:
        return f"[error] {e}"


SPREADSHEET_TOOLS = [read_csv, read_xlsx, csv_query, csv_describe]

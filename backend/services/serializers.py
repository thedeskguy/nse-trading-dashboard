import math
import numpy as np
import pandas as pd
from typing import Any


def _convert_value(v: Any) -> Any:
    """Convert a single value to JSON-safe Python native type."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        val = float(v)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, dict):
        return clean_dict(v)
    if isinstance(v, list):
        return [_convert_value(i) for i in v]
    return v


def df_to_records(df: pd.DataFrame) -> list[dict]:
    """
    Converts a DataFrame to a list of dicts suitable for JSON serialization.
    - DatetimeIndex is converted to ISO 8601 strings under key "timestamp"
    - NaN/inf/-inf are converted to None
    - numpy int64/float64 are converted to Python native types
    """
    records = []
    has_datetime_index = isinstance(df.index, pd.DatetimeIndex)

    for idx, row in df.iterrows():
        record: dict[str, Any] = {}

        if has_datetime_index:
            record["timestamp"] = idx.isoformat()
        else:
            record["timestamp"] = str(idx)

        for col, val in row.items():
            record[str(col)] = _convert_value(val)

        records.append(record)

    return records


def clean_dict(d: dict) -> dict:
    """
    Recursively converts NaN/inf to None and numpy types to Python native types.
    Handles nested dicts and lists.
    """
    result = {}
    for k, v in d.items():
        result[str(k)] = _convert_value(v)
    return result

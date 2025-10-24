import pandas as pd
import numpy as np

def clean_zscore(df: pd.DataFrame, z_threshold: float = 3.0):
    """
    Remove outliers using z-score on numeric columns.
    Returns cleaned DataFrame and stats dict.
    """
    if df.empty:
        return df.copy(), {"total_rows": 0, "removed_outliers": 0, "remaining_rows": 0}

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    z = (df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std(ddof=0)
    mask = (z.abs() <= z_threshold).all(axis=1)

    total = len(df)
    cleaned = df[mask].copy()
    removed = total - len(cleaned)

    stats = {
        "total_rows": total,
        "removed_outliers": removed,
        "remaining_rows": len(cleaned)
    }
    return cleaned, stats
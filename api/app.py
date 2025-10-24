# api/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from utils.db_connection import get_collection
import pandas as pd
import numpy as np
import os
from data.load_data import load_water_data
from data.clean_data import clean_zscore


# Single source of truth for our data store (mongomock)
COLL = get_collection()

# Numeric fields we support for filtering and statistics
NUMERIC_FIELDS = ["temperature_c", "salinity_ppt", "odo_mg_l"]
KEY_FIELDS = ["timestamp", "latitude", "longitude"] + NUMERIC_FIELDS

# --- Seed collection if empty (so data exists when the API starts) ---
def seed_collection_if_empty():
    if COLL.count_documents({}) > 0:
        return  # already has data

    cleaned_path = "data/cleaned_output.csv"
    raw_path = "2021-dec16.csv"  # <-- update this to your actual filename

    if os.path.exists(cleaned_path):
        df = pd.read_csv(cleaned_path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        df_raw = load_water_data(raw_path)
        df, _ = clean_zscore(df_raw, z_threshold=3.0)

    if not df.empty:
        COLL.insert_many(df.to_dict("records"))

seed_collection_if_empty()

# ------------------------------------------------------------------------------
# App bootstrap
# ------------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # allow cross-origin requests (from Streamlit later)


# ------------------------------------------------------------------------------
# Small helpers (parsing & dataframe loading)
# ------------------------------------------------------------------------------

def _parse_iso(s):
    """Parse an ISO-like timestamp, return None if invalid."""
    if not s:
        return None
    try:
        # Let pandas handle many formats; ISO works best
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return None

def _parse_float(s):
    """Parse float query params robustly."""
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def _load_df_from_db(query=None, skip=0, limit=None):
    """
    Pull documents from mongomock and convert to a pandas DataFrame.
    Only returns the fields we care about.
    """
    if query is None:
        query = {}

    cursor = COLL.find(query, {f: 1 for f in KEY_FIELDS})
    if skip:
        cursor = cursor.skip(int(skip))
    if limit:
        cursor = cursor.limit(int(limit))

    docs = list(cursor)
    if not docs:
        return pd.DataFrame(columns=KEY_FIELDS)

    df = pd.DataFrame(docs)
    # Normalize timestamp to pandas datetime if present
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    # Ensure numeric columns are numeric
    for col in NUMERIC_FIELDS + ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Drop Mongo’s _id from the DataFrame view (we don’t expose it here)
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True, errors="ignore")
    return df


# ------------------------------------------------------------------------------
# 1) Health check
# ------------------------------------------------------------------------------
@app.get("/api/health")
def health():
    """
    Quick liveness check for your demo.
    Response: { "status": "ok" }
    """
    return jsonify({"status": "ok"}), 200


# ------------------------------------------------------------------------------
# 2) Observations (with filters & pagination)
# ------------------------------------------------------------------------------
@app.get("/api/observations")
def observations():
    """
    Fetch cleaned observations with optional filters:
    - start, end: ISO timestamps (inclusive)
    - min_temp, max_temp
    - min_sal,  max_sal
    - min_odo,  max_odo
    - limit (default 100, max 1000), skip (offset)

    Response:
    {
      "count": <matches_before_pagination>,
      "items": [ { "timestamp": "...", "latitude": ..., "temperature_c": ... }, ... ]
    }
    """
    # --- Parse query params
    start = _parse_iso(request.args.get("start"))
    end   = _parse_iso(request.args.get("end"))

    min_temp = _parse_float(request.args.get("min_temp"))
    max_temp = _parse_float(request.args.get("max_temp"))
    min_sal  = _parse_float(request.args.get("min_sal"))
    max_sal  = _parse_float(request.args.get("max_sal"))
    min_odo  = _parse_float(request.args.get("min_odo"))
    max_odo  = _parse_float(request.args.get("max_odo"))

    limit = request.args.get("limit", default="100")
    skip  = request.args.get("skip", default="0")

    # sanitize pagination
    try:
        limit = int(limit)
        skip  = int(skip)
    except ValueError:
        return jsonify({"error": "limit and skip must be integers"}), 400
    limit = max(1, min(limit, 1000))
    skip  = max(0, skip)

    # --- Build Mongo query
    query = {}

    if start is not None or end is not None:
        ts = {}
        if start is not None:
            ts["$gte"] = pd.to_datetime(start).to_pydatetime()
        if end is not None:
            ts["$lte"] = pd.to_datetime(end).to_pydatetime()
        query["timestamp"] = ts

    if min_temp is not None or max_temp is not None:
        r = {}
        if min_temp is not None: r["$gte"] = min_temp
        if max_temp is not None: r["$lte"] = max_temp
        query["temperature_c"] = r

    if min_sal is not None or max_sal is not None:
        r = {}
        if min_sal is not None: r["$gte"] = min_sal
        if max_sal is not None: r["$lte"] = max_sal
        query["salinity_ppt"] = r

    if min_odo is not None or max_odo is not None:
        r = {}
        if min_odo is not None: r["$gte"] = min_odo
        if max_odo is not None: r["$lte"] = max_odo
        query["odo_mg_l"] = r

    # total matches before pagination
    total_matches = COLL.count_documents(query)

    # page of results
    df = _load_df_from_db(query, skip=skip, limit=limit)

    # Convert to JSON-serializable forms
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["timestamp"] = df["timestamp"].apply(
            lambda x: x.isoformat(timespec="seconds") if pd.notna(x) else None
    )

    items = df.to_dict(orient="records")

    return jsonify({"count": total_matches, "items": items}), 200


# ------------------------------------------------------------------------------
# 3) Statistics (count, mean, min, max, percentiles)
# ------------------------------------------------------------------------------
@app.get("/api/stats")
def stats():
    """
    Summary statistics for numeric fields: temperature_c, salinity_ppt, odo_mg_l
    Response:
    {
      "temperature_c": { "count": ..., "mean": ..., "min": ..., "max": ..., "p25": ..., "p50": ..., "p75": ... },
      "salinity_ppt":  { ... },
      "odo_mg_l":      { ... }
    }
    """
    df = _load_df_from_db()

    if df.empty:
        return jsonify({"error": "No data available"}), 404

    result = {}
    for col in NUMERIC_FIELDS:
        if col in df.columns and df[col].notna().any():
            s = df[col].dropna()
            result[col] = {
                "count": int(s.shape[0]),
                "mean": float(s.mean()),
                "min":  float(s.min()),
                "max":  float(s.max()),
                "p25":  float(s.quantile(0.25)),
                "p50":  float(s.quantile(0.50)),
                "p75":  float(s.quantile(0.75)),
            }
        else:
            result[col] = {"count": 0}

    return jsonify(result), 200


# ------------------------------------------------------------------------------
# 4) Outliers-on-demand (IQR or z-score)
# ------------------------------------------------------------------------------
@app.get("/api/outliers")
def outliers():
    """
    On-demand outlier detection.
    Query params:
      - field: one of temperature_c | salinity_ppt | odo_mg_l (required)
      - method: "iqr" (default) or "zscore"
      - k: IQR multiplier (default 1.5)
      - z: z-score threshold (default 3.0)
      - limit/skip work here too (optional)
    Response:
    {
      "field": "...",
      "method": "iqr" | "zscore",
      "thresholds": { ... },   # bounds used
      "count": <total flagged>,
      "items": [ { ... }, ... ]  # page of flagged records
    }
    """
    field = request.args.get("field")
    method = (request.args.get("method") or "iqr").lower()
    k = _parse_float(request.args.get("k")) or 1.5
    zthr = _parse_float(request.args.get("z")) or 3.0

    if field not in NUMERIC_FIELDS:
        return jsonify({"error": f"field must be one of {NUMERIC_FIELDS}"}), 400
    if method not in {"iqr", "zscore"}:
        return jsonify({"error": "method must be 'iqr' or 'zscore'"}), 400

    # Load all rows into DataFrame (small dataset; OK for this project)
    df = _load_df_from_db()
    if df.empty or field not in df.columns:
        return jsonify({"error": "No data available for the requested field"}), 404

    s = df[field].dropna()

    if s.empty:
        return jsonify({"error": "No numeric values present for the field"}), 404

    flagged_idx = pd.Index([])
    thresholds = {}

    if method == "iqr":
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - k * iqr
        upper = q3 + k * iqr
        thresholds = {"lower": float(lower), "upper": float(upper)}
        flagged_idx = df.index[(df[field] < lower) | (df[field] > upper)]
    else:
        mean = s.mean()
        std = s.std(ddof=0)
        if std == 0 or np.isnan(std):
            return jsonify({"error": "Std deviation is zero or NaN; z-score method not applicable"}), 400
        z = (df[field] - mean) / std
        thresholds = {"z": float(zthr), "mean": float(mean), "std": float(std)}
        flagged_idx = df.index[z.abs() > zthr]

    flagged_df = df.loc[flagged_idx].copy()

    # Pagination for the outliers list
    limit = request.args.get("limit", default="100")
    skip  = request.args.get("skip", default="0")
    try:
        limit = int(limit)
        skip  = int(skip)
    except ValueError:
        return jsonify({"error": "limit and skip must be integers"}), 400
    limit = max(1, min(limit, 1000))
    skip  = max(0, skip)

    total_flagged = int(flagged_df.shape[0])
    page = flagged_df.iloc[skip:skip+limit].copy()

    if "timestamp" in page.columns:
        page["timestamp"] = page["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return jsonify({
        "field": field,
        "method": method,
        "thresholds": thresholds,
        "count": total_flagged,
        "items": page.to_dict(orient="records")
    }), 200


# ------------------------------------------------------------------------------
# Main entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # By default runs at http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=True)
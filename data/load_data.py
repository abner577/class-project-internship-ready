import pandas as pd
from pathlib import Path

def load_water_data(csv_path: str) -> pd.DataFrame:
    """
    Loads the full telemetry CSV and extracts the relevant columns for analysis.
    Expected columns:
    Latitude, Longitude, Date m/d/y, Time hh:mm:ss, Temperature (c), Salinity (ppt), ODO mg/L
    """
    df = pd.read_csv(csv_path)

    # Normalize column names for easy access
    df.columns = [c.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for c in df.columns]

    # Build timestamp column
    if "date_m/d/y" in df.columns and "time_hh:mm:ss" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["date_m/d/y"] + " " + df["time_hh:mm:ss"], errors="coerce"
        )
    elif "date" in df.columns and "time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
    else:
        df["timestamp"] = pd.NaT

    # Select key fields safely (some may have different variants)
    possible_cols = {
        "latitude": ["latitude"],
        "longitude": ["longitude"],
        "temperature_c": ["temperature_c", "temperature", "temp_c"],
        "salinity_ppt": ["salinity_ppt", "sal_ppt", "salinity"],
        "odo_mg_l": ["odo_mg_l", "odo_mgl", "odo"],
    }

    selected = {}
    for target, options in possible_cols.items():
        for opt in options:
            if opt in df.columns:
                selected[target] = df[opt]
                break

    selected["timestamp"] = df["timestamp"]

    # Create final DataFrame
    clean_df = pd.DataFrame(selected)

    # Convert numeric fields properly
    for col in ["latitude", "longitude", "temperature_c", "salinity_ppt", "odo_mg_l"]:
        if col in clean_df.columns:
            clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

    # Drop rows missing critical info
    clean_df.dropna(subset=["timestamp", "latitude", "longitude"], inplace=True)

    return clean_df
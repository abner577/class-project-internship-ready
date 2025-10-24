# client/app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------------------
API_BASE = "http://127.0.0.1:5000/api"

st.set_page_config(
    page_title="Water Quality Dashboard",
    layout="wide",
    page_icon="💧",
)

st.title("💧 Water Quality Dashboard")
st.caption("Interactive client for your Flask REST API")


# ------------------------------------------------------------------------------
# SIDEBAR CONTROLS
# ------------------------------------------------------------------------------
st.sidebar.header("🔍 Filters")

# Date range
start_date = st.sidebar.text_input("Start timestamp (ISO)", "")
end_date = st.sidebar.text_input("End timestamp (ISO)", "")

# Numeric filters
min_temp = st.sidebar.number_input("Min Temperature (°C)", value=None, placeholder="e.g. 10")
max_temp = st.sidebar.number_input("Max Temperature (°C)", value=None, placeholder="e.g. 35")

min_sal = st.sidebar.number_input("Min Salinity (ppt)", value=None, placeholder="e.g. 20")
max_sal = st.sidebar.number_input("Max Salinity (ppt)", value=None, placeholder="e.g. 50")

min_odo = st.sidebar.number_input("Min ODO (mg/L)", value=None, placeholder="e.g. 0")
max_odo = st.sidebar.number_input("Max ODO (mg/L)", value=None, placeholder="e.g. 10")

limit = st.sidebar.number_input("Limit (rows)", value=100, min_value=1, max_value=1000)
skip = st.sidebar.number_input("Skip (offset)", value=0, min_value=0)

if st.sidebar.button("Fetch Observations"):
    # Build query parameters
    params = {
        "start": start_date or None,
        "end": end_date or None,
        "min_temp": min_temp or None,
        "max_temp": max_temp or None,
        "min_sal": min_sal or None,
        "max_sal": max_sal or None,
        "min_odo": min_odo or None,
        "max_odo": max_odo or None,
        "limit": limit,
        "skip": skip,
    }

    # Remove None keys
    params = {k: v for k, v in params.items() if v not in ("", None)}

    with st.spinner("Fetching data..."):
        try:
            r = requests.get(f"{API_BASE}/observations", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                st.success(f"✅ {data['count']} records total ({len(data['items'])} shown)")
                df = pd.DataFrame(data["items"])
                if not df.empty:
                    st.dataframe(df)

                    # ----------------------------------------------------------
                    # PLOTLY VISUALIZATIONS
                    # ----------------------------------------------------------
                    col1, col2, col3 = st.columns(3)

                    # Line: Temperature over Time
                    with col1:
                        if "timestamp" in df.columns:
                            fig = px.line(df, x="timestamp", y="temperature_c", title="Temperature Over Time")
                            st.plotly_chart(fig, use_container_width=True)

                    # Histogram: Salinity
                    with col2:
                        if "salinity_ppt" in df.columns:
                            fig = px.histogram(df, x="salinity_ppt", nbins=20, title="Salinity Distribution")
                            st.plotly_chart(fig, use_container_width=True)

                    # Scatter: Temperature vs Salinity
                    with col3:
                        if "temperature_c" in df.columns and "salinity_ppt" in df.columns:
                            fig = px.scatter(
                                df,
                                x="temperature_c",
                                y="salinity_ppt",
                                color="odo_mg_l" if "odo_mg_l" in df.columns else None,
                                title="Temperature vs Salinity (colored by ODO)",
                                hover_data=["latitude", "longitude"],
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No data available for the given filters.")
            else:
                st.error(f"API returned {r.status_code}: {r.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")


# ------------------------------------------------------------------------------
# STATS PANEL
# ------------------------------------------------------------------------------
st.subheader("📊 Summary Statistics")

if st.button("Fetch Statistics"):
    with st.spinner("Getting statistics..."):
        try:
            r = requests.get(f"{API_BASE}/stats", timeout=10)
            if r.status_code == 200:
                stats = r.json()
                st.json(stats)
            else:
                st.error(f"API returned {r.status_code}: {r.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")


# ------------------------------------------------------------------------------
# OUTLIERS PANEL
# ------------------------------------------------------------------------------
st.subheader("🚨 Outlier Detection")

field = st.selectbox("Select field", ["temperature_c", "salinity_ppt", "odo_mg_l"])
method = st.selectbox("Method", ["iqr", "zscore"])
k = st.number_input("IQR Multiplier (k)", value=1.5)
z = st.number_input("Z-score Threshold", value=3.0)
if st.button("Check Outliers"):
    params = {"field": field, "method": method, "k": k, "z": z}
    with st.spinner("Detecting outliers..."):
        try:
            r = requests.get(f"{API_BASE}/outliers", params=params, timeout=10)
            if r.status_code == 200:
                res = r.json()
                st.success(f"{res['count']} outliers found for {field}")
                df_out = pd.DataFrame(res["items"])
                st.dataframe(df_out)
            else:
                st.error(f"API returned {r.status_code}: {r.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")
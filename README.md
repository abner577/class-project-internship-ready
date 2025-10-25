# Water Quality Data Pipeline

This project transforms raw aquatic sensor data into a fully interactive data service.  
It demonstrates an end-to-end data engineering workflow:  
**CSV → Cleaning → NoSQL (MongoMock) → Flask REST API → Streamlit Client (Visualization)**

---

## Project Overview

The system loads raw water-quality CSV data, cleans outliers using the z-score method, stores the cleaned data in an in-memory NoSQL database (MongoMock), and exposes it through a Flask API.  
A Streamlit dashboard then consumes the API and visualizes temperature, salinity, and other metrics through interactive Plotly charts.

### 🔧 Components

| Component | Description |
|------------|-------------|
| **`/data/`** | Contains raw and cleaned CSV datasets |
| **`/utils/`** | Helper script for DB connection |
| **`/api/`** | Flask REST API that exposes cleaned data and statistics |
| **`/client/`** | Streamlit web client for interactive visualization |
| **`main.py`** | Runs the ETL process (load, clean, and insert data into MongoMock) |
| **`requirements.txt`** | Lists Python dependencies |

---

## 🧩 Tech Stack

- **Python 3.12**
- **Flask 3.1.2** – REST API framework  
- **Streamlit 1.50.0** – Interactive dashboard  
- **Pandas 2.3.3** – Data cleaning and analysis  
- **MongoMock 4.1.2** – In-memory NoSQL database  
- **Plotly 6.0.0** – Interactive charts  
- **Requests** – Client-side API calls  

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

### 2. Create and Activate a Virtual Environment
**On macOS/Linux (WSL):**
```bash
python -m venv .venv
source .venv/bin/activate

*On Windows**
python -m venv .venv
.venv\Scripts\activate

### 3. Install Dependencies 
pip install -r requirements.txt

---

# 🧹 Part 1 — Data Loading & Cleaning
# Run the data pipeline
python main.py

# This script will:
# - Load the CSV files from /data/
# - Clean the data using z-score filtering (|z| > 3)
# - Print summary stats to the console
# - Insert cleaned records into MongoMock
# - Save a cleaned version to /data/cleaned_output.csv


# 🌐 Part 2 — Flask REST API
# Start the API server
python -m api.app

# Once running, access the endpoints in your browser or using curl.

# 🔹 API Endpoints
# /api/health        -> Returns { "status": "ok" }
# /api/observations  -> Returns records with optional filters
# /api/stats         -> Returns summary statistics for numeric fields
# /api/outliers      -> Detects outliers using z-score or IQR

# Example Queries
curl "http://127.0.0.1:5000/api/observations?limit=5"
curl "http://127.0.0.1:5000/api/stats"
curl "http://127.0.0.1:5000/api/outliers?field=temperature_c&method=zscore"


# 📊 Part 3 — Streamlit Client
# Run the Streamlit dashboard
streamlit run client/app.py

# Then open http://localhost:8501 in your browser.

# Features:
# - Sidebar filters for temperature, salinity, and ODO ranges
# - Data table showing filtered results
# - 3 Plotly charts:
#     • Temperature over time (Line)
#     • Salinity distribution (Histogram)
#     • Temperature vs. Salinity (Scatter)
# - Statistics Panel: calls /api/stats to show summary metrics
# - Outliers View: calls /api/outliers and displays flagged records
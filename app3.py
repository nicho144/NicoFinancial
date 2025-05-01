import streamlit as st
import hashlib
import json
import requests
import pandas as pd
import os
import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import io  # Import for StringIO

# Ensure Streamlit components are installed
import matplotlib
matplotlib.use('Agg')  # Necessary for saving matplotlib plots in Streamlit

# Configuration and Constants
DATA_SOURCES = {
    "VIX_Term_Structure": "https://www.example.com/vix_term_structure",
    "ES_Term_Structure": "https://www.example.com/es_term_structure",
    "DXY": "https://www.example.com/dxy",
    "BONDS": "https://www.example.com/bonds",
    "GOLD": "https://www.example.com/gold",
    "FED_FUNDS_FUTURES": "https://www.example.com/fed_funds_futures",
    "TREASURY_YIELD_CURVE": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/DailyTreasuryYieldCurveRateData.csv"
}

DATA_DIR = "./data_snapshots"
AUDIT_LOG = "./logs/audit_log.json"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("./logs", exist_ok=True)

# Util: Fetch data from a URL
def fetch_data(url: str) -> Optional[str]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        st.error(f"Error fetching {url}: {e}")
        return None

# Util: Generate checksum
def generate_checksum(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Util: Save raw snapshot
def save_snapshot(name: str, content: str):
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{DATA_DIR}/{name}_{timestamp}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return filename

# Util: Update audit log
def log_audit_entry(source: str, checksum: str, snapshot_file: str):
    entry = {
        "source": source,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "checksum": checksum,
        "snapshot_file": snapshot_file
    }
    try:
        if os.path.exists(AUDIT_LOG):
            with open(AUDIT_LOG, 'r') as log_file:
                data = json.load(log_file)
        else:
            data = []
        data.append(entry)
        with open(AUDIT_LOG, 'w') as log_file:
            json.dump(data, log_file, indent=2)
    except Exception as e:
        st.error(f"Audit log update failed: {e}")

# Util: Parse implied Fed Funds Rate from futures HTML (example placeholder)
def parse_implied_fed_rate(html: str) -> Optional[float]:
    try:
        soup = BeautifulSoup(html, 'html.parser')
        rate_text = soup.find('div', class_='implied-rate').text.strip('% ')
        return float(rate_text)
    except Exception as e:
        st.error(f"Parsing implied Fed rate failed: {e}")
        return None

# Parse and compare Treasury yield curves
def process_yield_curve(csv_data: str):
    try:
        # Read the CSV data into a DataFrame
        df = pd.read_csv(io.StringIO(csv_data))
        
        # Ensure the data is sorted by Date (to handle any out-of-order data)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        # Define the maturities to analyze
        maturities = [col for col in df.columns if "Yr" in col or "Mo" in col]

        # Extract today's and yesterday's yields
        latest = df.iloc[-1]
        previous = df.iloc[-2]

        today_yields = latest[maturities].astype(float)
        yesterday_yields = previous[maturities].astype(float)

        # Plot the yield curve comparison
        plt.figure(figsize=(12, 6))
        plt.plot(maturities, today_yields, marker='o', label='Today')
        plt.plot(maturities, yesterday_yields, marker='x', label='Yesterday')
        plt.title("US Treasury Yield Curve: Today vs Yesterday")
        plt.xlabel("Maturity")
        plt.ylabel("Yield (%)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("./yield_curve_comparison.png")

        # Calculate the spread for 10Y - 2Y
        spread_today = today_yields["10 Yr"] - today_yields["2 Yr"]
        spread_yesterday = yesterday_yields["10 Yr"] - yesterday_yields["2 Yr"]

        # Determine if the curve is steepening or flattening
        steepener = spread_today > spread_yesterday

        st.write(f"Yield Curve Spread (10Y - 2Y) Today: {spread_today:.2f}% | Yesterday: {spread_yesterday:.2f}%")
        st.write("Steepener" if steepener else "Flattener")
        
        return spread_today, steepener

    except Exception as e:
        st.error(f"Error processing the yield curve data: {e}")
        return None, None

# Main Ingestion Function
def ingest_all_sources():
    for name, url in DATA_SOURCES.items():
        st.write(f"Fetching: {name}")
        content = fetch_data(url)
        if content:
            checksum = generate_checksum(content)
            snapshot_file = save_snapshot(name, content)
            log_audit_entry(name, checksum, snapshot_file)

            if name == "FED_FUNDS_FUTURES":
                implied_rate = parse_implied_fed_rate(content)
                if implied_rate:
                    st.write(f"Parsed Implied Fed Rate: {implied_rate:.2f}%")

            if name == "TREASURY_YIELD_CURVE":
                spread, steepener = process_yield_curve(content)

            st.write(f"{name} fetched and logged.")
        else:
            st.error(f"Failed to fetch {name}.")

# Streamlit file uploader
def upload_file():
    uploaded_file = st.file_uploader("Choose a file", type=["csv", "txt", "html", "json"])
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8")
        st.text_area("File content", content, height=300)

        # Process file if it's a CSV (example)
        if uploaded_file.type == "text/csv":
            df = pd.read_csv(io.StringIO(content))
            st.write(df.head())  # Display the first few rows of the file
        # Process other file types here

if __name__ == "__main__":
    st.title("Financial Data Pipeline Dashboard")
    upload_file()  # Upload file section
    ingest_all_sources()  # Call your ingestion pipeline

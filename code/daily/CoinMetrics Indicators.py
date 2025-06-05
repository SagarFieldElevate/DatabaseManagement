import os
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
)

# For community API, no key is needed. For paid API, use your actual key
API_KEY = os.getenv("COINMETRICS_API_KEY")

# Use community API if no key is provided
if API_KEY:
    BASE_URL = "https://api.coinmetrics.io/v4"
    headers = {"X-CoinMetrics-Api-Key": API_KEY}
else:
    BASE_URL = "https://community-api.coinmetrics.io/v4"
    headers = {}

def fetch(endpoint: str, params: dict) -> dict:
    """Fetch data from CoinMetrics API with better error handling"""
    try:
        resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error: {e}")
        return {"data": []}

# Get recent data (last 7 days)
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=4000)

# Format times as required by API
start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

# Asset metrics parameters - using ONLY metrics available in community API
asset_params = {
    "assets": "btc",
    "metrics": "AdrActCnt,TxCnt,SplyCur,PriceUSD,CapMrktCurUSD",
    "frequency": "1d", 
    "start_time": start_time_str,
    "end_time": end_time_str,
    "page_size": 10000,
}

print("Fetching asset metrics...")
asset_response = fetch(f"{BASE_URL}/timeseries/asset-metrics", asset_params)
asset_data = asset_response.get("data", [])

print(f"Asset data points: {len(asset_data)}")

# Create DataFrame with all data points
records = []

# Process all data points
for asset_point in asset_data:
    record = {
        "Date": asset_point.get("time"),
        "Active Addresses": asset_point.get("AdrActCnt"),
        "Transaction Count": asset_point.get("TxCnt"),
        "Current Supply": asset_point.get("SplyCur"),
        "Price USD": asset_point.get("PriceUSD"),
        "Market Cap USD": asset_point.get("CapMrktCurUSD"),
    }
    records.append(record)

# Create DataFrame
df = pd.DataFrame(records)

# Convert Date to datetime and numeric columns
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df = df.reset_index(drop=True)
    
    # Convert numeric columns to float
    numeric_columns = ['Active Addresses', 'Transaction Count', 'Current Supply', 
                      'Price USD', 'Market Cap USD']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Get only the latest data point
    latest_df = df.iloc[[-1]].copy()
    
    print("\nLatest data point:")
    print(latest_df)
    
    # Save to Excel
    filename = "coinmetrics_indicators.xlsx"
    latest_df.to_excel(filename, index=False)
    
    # GitHub upload workflow
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
    BASE_ID = "appnssPRD9yeYJJe5"
    TABLE_NAME = "daily"
    airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    
    GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
    BRANCH = "main"
    UPLOAD_PATH = "Uploads"
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    INDICATOR_NAME = "CoinMetrics Indicators"
    
    # Upload to GitHub
    github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
    raw_url = github_response['content']['raw_url']
    file_sha = github_response['content']['sha']
    
    # Update or create Airtable record
    airtable_headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
    response = requests.get(airtable_url, headers=airtable_headers)
    records_airtable = response.json().get('records', [])
    existing_records = [rec for rec in records_airtable if rec['fields'].get('Name') == INDICATOR_NAME]
    record_id = existing_records[0]['id'] if existing_records else None
    
    if record_id:
        update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
    else:
        create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
    
    # Cleanup
    delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
    os.remove(filename)
    
    print("✅ CoinMetrics indicators uploaded.")
else:
    print("❌ No data received from CoinMetrics API")

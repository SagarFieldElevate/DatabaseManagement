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

# Use env variable if available, otherwise fall back to provided demo key
API_KEY = os.getenv("COINMETRICS_API_KEY", "BLgxPvn1qdWWzTqh7fx3")
BASE_URL = "https://api.coinmetrics.io/v4"
headers = {"X-CoinMetrics-Api-Key": API_KEY}

def fetch(endpoint: str, params: dict) -> dict:
    """Fetch data from CoinMetrics API with better error handling"""
    try:
        resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return {"data": []}
    except ValueError as e:
        print(f"JSON decode error: {e}")
        return {"data": []}

# Get recent data (last 7 days) for better results
end_time = datetime.now(timezone.utc)  # Fixed datetime deprecation
start_time = end_time - timedelta(days=7)

# Format dates for API
date_format = "%Y-%m-%d"
start_date = start_time.strftime(date_format)
end_date = end_time.strftime(date_format)

print(f"Fetching data from {start_date} to {end_date}")

# Asset metrics parameters - combining all metrics in one call
asset_params = {
    "assets": "btc",
    "metrics": "AdrActCnt,TxCnt,HashRateMean,SplyCur,CapMVRVCur,PriceUSD,CapMrktCurUSD,VolTotUSD",
    "frequency": "1d",
    "start_time": start_date,
    "end_time": end_date,
    "page_size": 100,
}

# Market candles parameters (optional - in case it works)
market_params = {
    "markets": "coinbase-btc-usd-spot",
    "frequency": "1d", 
    "start_time": start_date,
    "end_time": end_date,
    "page_size": 100,
}

print("Fetching asset metrics...")
asset_response = fetch(f"{BASE_URL}/timeseries/asset-metrics", asset_params)
asset_data = asset_response.get("data", [])

print("Fetching market data...")
market_response = fetch(f"{BASE_URL}/timeseries/market-candles", market_params)
market_data = market_response.get("data", [])

print(f"Asset data points: {len(asset_data)}")
print(f"Market data points: {len(market_data)}")

# Create records from asset data
records = []

# Process asset data (primary source)
for asset_point in asset_data:
    # Find corresponding market data if available
    market_point = {}
    asset_time = asset_point.get("time")
    if market_data and asset_time:
        for mp in market_data:
            if mp.get("time") == asset_time:
                market_point = mp
                break
    
    # Create record with all available data
    record = {
        "Date": asset_time,
        "Active Addresses": asset_point.get("AdrActCnt"),
        "Transaction Count": asset_point.get("TxCnt"), 
        "Hash Rate": asset_point.get("HashRateMean"),
        "Current Supply": asset_point.get("SplyCur"),
        "MVRV Current": asset_point.get("CapMVRVCur"),
        "Price USD": asset_point.get("PriceUSD"),
        "Market Cap USD": asset_point.get("CapMrktCurUSD"),
        "Volume USD": asset_point.get("VolTotUSD"),
    }
    
    # Add market candle data if available and not None
    if market_point:
        if market_point.get("close") is not None:
            record["Close Price"] = market_point.get("close")
        if market_point.get("open") is not None:
            record["Open Price"] = market_point.get("open")
        if market_point.get("high") is not None:
            record["High Price"] = market_point.get("high")
        if market_point.get("low") is not None:
            record["Low Price"] = market_point.get("low")
        if market_point.get("volume") is not None:
            record["Candle Volume"] = market_point.get("volume")
    
    records.append(record)

# Create DataFrame
df = pd.DataFrame(records)

if not df.empty:
    # Convert Date to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert numeric columns to float (handling None values)
    numeric_columns = [
        'Active Addresses', 'Transaction Count', 'Hash Rate', 
        'Current Supply', 'MVRV Current', 'Price USD', 
        'Market Cap USD', 'Volume USD', 'Close Price', 
        'Open Price', 'High Price', 'Low Price', 'Candle Volume'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Remove columns that are entirely None/NaN
    df = df.dropna(axis=1, how='all')
    
    # Sort by date
    df = df.sort_values('Date')
    df = df.reset_index(drop=True)
    
    # Get only the latest data point (as in original code)
    latest_record = df.iloc[-1:].copy()
    
    # Remove any fields that are NaN from the latest record
    latest_record = latest_record.dropna(axis=1)
    
    print("\nLatest data point:")
    print(latest_record)
    
    # Save to Excel
    filename = "coinmetrics_indicators.xlsx"
    latest_record.to_excel(filename, index=False)
    
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

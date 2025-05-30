import os
import requests
import pandas as pd
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

def fetch(endpoint: str, params: dict) -> list:
    try:
        resp = requests.get(endpoint, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except (requests.exceptions.RequestException, ValueError):
        return []

asset_params = {
    "assets": "btc",
    "metrics": "AdrActCnt,TxCnt,HashRateMean,SplyCur,CapMVRVCur",
    "frequency": "1d",
    "page_size": 1,
}

market_params = {
    "markets": "coinbase-btc-usd-spot",
    "frequency": "1d",
    "page_size": 1,
}

asset_data = fetch(f"{BASE_URL}/timeseries/asset-metrics", asset_params)
market_data = fetch(f"{BASE_URL}/timeseries/market-candles", market_params)

latest_asset = asset_data[-1] if asset_data else {}
latest_market = market_data[-1] if market_data else {}

records = [
    {
        "Date": latest_asset.get("time") or latest_market.get("time"),
        "Active Addresses": latest_asset.get("AdrActCnt"),
        "Transaction Count": latest_asset.get("TxCnt"),
        "Hash Rate": latest_asset.get("HashRateMean"),
        "Current Supply": latest_asset.get("SplyCur"),
        "MVRV Current": latest_asset.get("CapMVRVCur"),
        "Close Price": latest_market.get("close"),
    }
]


df = pd.DataFrame(records)
filename = "coinmetrics_indicators.xlsx"
df.to_excel(filename, index=False)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "CoinMetrics Indicators"

github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

airtable_headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
response = requests.get(airtable_url, headers=airtable_headers)
records_airtable = response.json().get('records', [])
existing_records = [rec for rec in records_airtable if rec['fields'].get('Name') == INDICATOR_NAME]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ CoinMetrics indicators uploaded.")

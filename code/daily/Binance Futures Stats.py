import os
import requests
import pandas as pd
from datetime import datetime
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

symbols = ["BTCUSDT", "ETHUSDT"]
records = []
for symbol in symbols:
    # Funding rate
    r = requests.get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1")
    funding = r.json()[0]
    # Open interest
    oi = requests.get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=1").json()[0]
    # Order book snapshot
    ob = requests.get(f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=5").json()
    # Liquidations placeholder (Binance API v2; may require key)
    liquidations = requests.get(f"https://fapi.binance.com/futures/data/orderLiquidation?symbol={symbol}&limit=1").json()[0]
    records.append({
        "Symbol": symbol,
        "Funding Rate": funding.get("fundingRate"),
        "Open Interest": oi.get("sumOpenInterestValue"),
        "Bid 1": ob.get("bids", [[None]])[0][0],
        "Ask 1": ob.get("asks", [[None]])[0][0],
        "Last Liquidation Price": liquidations.get("price")
    })

# === Save to Excel ===
df = pd.DataFrame(records)
filename = "binance_futures_stats.xlsx"
df.to_excel(filename, index=False)

# === Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "Binance Futures Stats"

# === Upload ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Airtable Check ===
airtable_headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
response = requests.get(airtable_url, headers=airtable_headers)
records_airtable = response.json().get('records', [])
existing_records = [rec for rec in records_airtable if rec['fields'].get('Name') == INDICATOR_NAME]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Binance Futures stats uploaded.")

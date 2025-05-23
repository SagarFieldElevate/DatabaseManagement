from pycoingecko import CoinGeckoAPI
import pandas as pd
import os
import requests
from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
    ensure_utc,
)

# === Initialize CoinGecko with API key ===
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "CG-eFCtjc4Mocq5xr7kno7b8qUm")
cg = CoinGeckoAPI(api_key=COINGECKO_API_KEY)

# === Fetch 365 days of daily prices for BTC and ETH ===
coins = {"BTC": "bitcoin", "ETH": "ethereum"}
records = []
for symbol, coin_id in coins.items():
    market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency="usd", days=365)
    for ts, price in market_data["prices"]:
        records.append({
            "Date": pd.to_datetime(ts, unit="ms", utc=True),
            "Symbol": symbol,
            "Close Price (USD)": price
        })

# === Save to Excel ===
df = pd.DataFrame(records)
df = ensure_utc(df)
filename = "coingecko_prices_daily.xlsx"
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

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Check if record exists in Airtable ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records_airtable = response.json().get('records', [])

existing_records = [
    rec for rec in records_airtable
    if rec['fields'].get('Name') == "CoinGecko BTC & ETH Price Daily"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Update or create record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("CoinGecko BTC & ETH Price Daily", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ CoinGecko BTC & ETH daily prices uploaded to Airtable and GitHub cleaned up.")

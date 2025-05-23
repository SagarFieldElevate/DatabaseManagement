from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Initialize CoinGecko with API key ===
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "CG-eFCtjc4Mocq5xr7kno7b8qUm")
cg = CoinGeckoAPI(api_key=COINGECKO_API_KEY)

# === Fetch BTC price history and compute daily returns ===
market_data = cg.get_coin_market_chart_by_id(id="bitcoin", vs_currency="usd", days=365)
prices = market_data["prices"]

price_df = pd.DataFrame(prices, columns=["timestamp", "price"])
price_df["Date"] = pd.to_datetime(price_df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d")
price_df["Return"] = price_df["price"].pct_change() * 100
price_df = price_df.dropna()[["Date", "Return"]]

filename = "bitcoin_daily_returns.xlsx"
price_df.to_excel(filename, index=False)

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
    if rec['fields'].get('Name') == "CoinGecko BTC Daily Returns"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Update or create record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("CoinGecko BTC Daily Returns", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ CoinGecko BTC daily returns uploaded to Airtable and GitHub cleaned up.")

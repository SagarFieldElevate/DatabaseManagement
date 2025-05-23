from pycoingecko import CoinGeckoAPI
import pandas as pd
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Initialize CoinGecko with API key ===
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "CG-eFCtjc4Mocq5xr7kno7b8qUm")
cg = CoinGeckoAPI(api_key=COINGECKO_API_KEY)

# === Fetch top 100 coins by market cap ===
markets = cg.get_coins_markets(vs_currency="usd", order="market_cap_desc", per_page=100, page=1)
records = [{
    "Symbol": entry["symbol"].upper(),
    "Name": entry["name"],
    "Price (USD)": entry["current_price"]
} for entry in markets]

df = pd.DataFrame(records)
filename = "coingecko_top100_altcoin_prices.xlsx"
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
    if rec['fields'].get('Name') == "CoinGecko Top100 Altcoin Prices"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Update or create record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("CoinGecko Top100 Altcoin Prices", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ CoinGecko top 100 altcoin prices uploaded to Airtable and GitHub cleaned up.")

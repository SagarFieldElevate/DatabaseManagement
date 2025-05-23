from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "CG-eFCtjc4Mocq5xr7kno7b8qUm")
cg = CoinGeckoAPI(api_key=COINGECKO_API_KEY)

stablecoins = {
    "USDT": "tether",
    "USDC": "usd-coin",
    "DAI": "dai",
    "TUSD": "true-usd"
}

records = []
for symbol, coin_id in stablecoins.items():
    data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency="usd", days=365)
    for ts, price in data["prices"]:
        deviation = price - 1
        records.append({
            "Date": datetime.utcfromtimestamp(ts/1000).strftime("%Y-%m-%d"),
            "Symbol": symbol,
            "Peg Deviation": deviation
        })

df = pd.DataFrame(records)
filename = "stablecoin_peg_deviation.xlsx"
df.to_excel(filename, index=False)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records_airtable = response.json().get('records', [])

existing_records = [
    rec for rec in records_airtable
    if rec['fields'].get('Name') == "CoinGecko Stablecoin Peg Deviation"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("CoinGecko Stablecoin Peg Deviation", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ CoinGecko stablecoin peg deviation uploaded to Airtable and GitHub cleaned up.")

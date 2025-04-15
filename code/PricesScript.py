from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from io import BytesIO
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Initialize CoinGecko ===
cg = CoinGeckoAPI()

# === Coin list ===
coins = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'ADA': 'cardano',
    'SOL': 'solana',
    'DOT': 'polkadot',
    'AVAX': 'avalanche-2'
}

# === Fetch OHLC data (daily for 365 days) ===
def fetch_ohlc(coin_id):
    ohlc = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency='usd', days=365)
    df = pd.DataFrame(ohlc, columns=['timestamp', 'open', 'high', 'low', 'close'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
    df.drop(columns=['timestamp'], inplace=True)
    return df

ohlc_data = []
for symbol, coin_id in coins.items():
    df = fetch_ohlc(coin_id)
    df['symbol'] = symbol
    ohlc_data.append(df)

new_data_df = pd.concat(ohlc_data, ignore_index=True)

# === Airtable config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Database"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

# === Check Airtable for existing record ===
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records = response.json().get('records', [])

existing_records = [
    rec for rec in records
    if rec['fields'].get('Name') == "OHLC Master Data with History"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Append existing data if present ===
if record_id:
    existing_attachment = existing_records[0]['fields'].get('Database Attachment', [])
    if existing_attachment:
        existing_url = existing_attachment[0]['url']
        existing_file = requests.get(existing_url)
        existing_file.raise_for_status()
        existing_df = pd.read_excel(BytesIO(existing_file.content))
        combined_df = pd.concat([existing_df, new_data_df], ignore_index=True)
    else:
        combined_df = new_data_df
else:
    combined_df = new_data_df

# === Save to Excel ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"crypto_ohlc_365days_with_history_{timestamp}.xlsx"
combined_df.to_excel(filename, index=False)

# === GitHub config ===
GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Update or create Airtable record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("OHLC Master Data with History", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ All done! Airtable attachment replaced and cleanup complete.")

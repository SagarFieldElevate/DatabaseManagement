from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Initialize CoinGecko ===
cg = CoinGeckoAPI()

# === Define coin IDs ===
coins = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'ADA': 'cardano',
    'SOL': 'solana',
    'DOT': 'polkadot',
    'AVAX': 'avalanche-2'
}

# === Fetch 365 days of market cap data ===
data = []
for symbol, coin_id in coins.items():
    print(f"Fetching data for {symbol}...")
    
    # Fetch market data (price and volume) for the last 365 days
    market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=365)

    # Fetch circulating supply (static or slow-changing)
    coin_data = cg.get_coin_by_id(id=coin_id, localization=False)
    circulating_supply = coin_data['market_data']['circulating_supply']
    
    # Prepare base DataFrame
    price_data = market_data['prices']
    volume_data = market_data['total_volumes']
    
    df = pd.DataFrame(price_data, columns=['timestamp', 'price'])
    df['Date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d')
    df['Volume (USD)'] = [v[1] for v in volume_data]
    df['Market Cap (USD)'] = df['price'] * circulating_supply
    df['Cryptocurrency Symbol'] = symbol

    # Round values
    df['Price (USD)'] = df['price'].round(2)
    df['Volume (USD)'] = df['Volume (USD)'].round(2)
    df['Market Cap (USD)'] = df['Market Cap (USD)'].round(2)
    
    # Keep only the relevant columns
    df = df[['Date', 'Cryptocurrency Symbol', 'Price (USD)', 'Volume (USD)', 'Market Cap (USD)']]
    
    data.append(df)

# === Combine data into one DataFrame ===
combined_df = pd.concat(data, ignore_index=True)

# === Save to Excel ===
filename = "crypto_market_cap_365d.xlsx"
combined_df = ensure_utc(combined_df)
combined_df.to_excel(filename, index=False)

# === Config for Airtable + GitHub ===
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
raw_url = github_response['content']['download_url']
file_sha = github_response['content']['sha']

# === Check for existing record in Airtable ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records = response.json().get('records', [])

existing_records = [
    rec for rec in records
    if rec['fields'].get('Name') == "Cryptocurrency Market Cap (365 Days)"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Update or create Airtable record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Cryptocurrency Market Cap (365 Days)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Clean-up ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Cryptocurrency market cap data uploaded to GitHub, Airtable updated, and files cleaned up.")

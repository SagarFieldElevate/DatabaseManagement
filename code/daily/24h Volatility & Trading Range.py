from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# Initialize CoinGecko
cg = CoinGeckoAPI()

# Define coins
coins = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'ADA': 'cardano',
    'SOL': 'solana',
    'DOT': 'polkadot',
    'AVAX': 'avalanche-2'
}

# Fetch 365 days of OHLC data and compute metrics
data = []
for symbol, coin_id in coins.items():
    market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=365)
    ohlc_data = market_data['prices']
    
    for i in range(1, len(ohlc_data)):
        prev_day = ohlc_data[i-1]
        current_day = ohlc_data[i]
        
        prev_timestamp, prev_price = prev_day
        current_timestamp, current_price = current_day
        
        high = max(prev_price, current_price)
        low = min(prev_price, current_price)
        
        volatility = ((high - low) / low) * 100 if low > 0 else 0
        trading_range = high - low
        
        # Use date only, no timestamp
        date_only = datetime.utcfromtimestamp(current_timestamp / 1000).date().isoformat()
        
        data.append({
            'Date': date_only,
            f'{symbol} Close Price (USD)': round(current_price, 2),
            f'{symbol} High Price 24h (USD)': round(high, 2),
            f'{symbol} Low Price 24h (USD)': round(low, 2),
            f'{symbol} Volatility 24h (%)': round(volatility, 2),
            f'{symbol} Trading Range 24h (USD)': round(trading_range, 2)
        })

# Create DataFrame and export to Excel
df = pd.DataFrame(data)
filename = "crypto_365d_volatility_trading_range.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# === Airtable + GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Upload to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# Check if record exists
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "365-Day Crypto Volatility and Range"
]
record_id = existing_records[0]['id'] if existing_records else None

# Always replace attachment — either update or create
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("365-Day Crypto Volatility and Range", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Clean-up
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ All done! Airtable attachment replaced and cleanup complete.")

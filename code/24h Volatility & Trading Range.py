from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# Initialize CoinGecko
cg = CoinGeckoAPI()

# Define coins and metadata
coins = {
    'BTC': {'id': 'bitcoin', 'name': 'Bitcoin'},
    'ETH': {'id': 'ethereum', 'name': 'Ethereum'},
    'ADA': {'id': 'cardano', 'name': 'Cardano'},
    'SOL': {'id': 'solana', 'name': 'Solana'},
    'DOT': {'id': 'polkadot', 'name': 'Polkadot'},
    'AVAX': {'id': 'avalanche-2', 'name': 'Avalanche'}
}

data = []
for symbol, info in coins.items():
    coin_id = info['id']
    coin_name = info['name']
    market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=365)
    prices = market_data['prices']
    
    for i in range(1, len(prices)):
        prev_ts, prev_price = prices[i - 1]
        current_ts, current_price = prices[i]
        
        high = max(prev_price, current_price)
        low = min(prev_price, current_price)
        volatility = ((high - low) / low) * 100 if low > 0 else 0
        trading_range = high - low
        date = datetime.utcfromtimestamp(current_ts / 1000).date().isoformat()
        
        # Append full metadata per row
        data.append({
            'Date': date,
            'Crypto_Asset': coin_name,
            'Close_Price_USD': round(current_price, 2),
            'High_Price_24h_USD': round(high, 2),
            'Low_Price_24h_USD': round(low, 2),
            'Volatility_24h_Percent': round(volatility, 2),
            'Trading_Range_24h_USD': round(trading_range, 2),
            'Metric': f"{coin_name} 24h Volatility and Trading Range",
            'Description': f"Daily volatility and price range for {coin_name} over the past 24 hours. "
                           f"Volatility is computed as (High - Low) / Low * 100. "
                           f"Range is computed as High - Low. All prices are in USD.",
            'Unit': 'USD / Percent',
            'Source': 'CoinGecko API'
        })

# Create tagged DataFrame
df = pd.DataFrame(data)

# Export to Excel
filename = "crypto_365d_volatility_trading_range_tagged.xlsx"
df.to_excel(filename, index=False)

# === Airtable + GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Database"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Upload to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# Check if Airtable record exists
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

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("365-Day Crypto Volatility and Range", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Tagged file uploaded and cleaned up.")

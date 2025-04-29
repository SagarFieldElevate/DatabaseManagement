import pandas as pd
from datetime import datetime
import os
import requests
from pycoingecko import CoinGeckoAPI
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize CoinGecko API
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
    try:
        market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=365)
        ohlc_data = market_data['prices']
        logging.info(f"Fetched data for {symbol}.")

        for i in range(1, len(ohlc_data)):
            prev_day = ohlc_data[i - 1]
            current_day = ohlc_data[i]

            prev_timestamp, prev_price = prev_day
            current_timestamp, current_price = current_day

            high = max(prev_price, current_price)
            low = min(prev_price, current_price)

            volatility = ((high - low) / low) * 100 if low > 0 else 0
            trading_range = high - low

            data.append({
                'Date (YYYY-MM-DD)': datetime.utcfromtimestamp(current_timestamp / 1000).strftime('%Y-%m-%d'),
                f'{symbol} Close Price (USD)': round(current_price, 2),
                f'{symbol} High Price (USD)': round(high, 2),
                f'{symbol} Low Price (USD)': round(low, 2),
                f'{symbol} Volatility (24h %)': round(volatility, 2),
                f'{symbol} Trading Range (24h USD)': round(trading_range, 2)
            })

    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")

# Normalize and reshape data
df = pd.DataFrame(data)
df = df.melt(id_vars=['Date (YYYY-MM-DD)'], var_name='Metric', value_name='Value')
df = df.sort_values(['Date (YYYY-MM-DD)', 'Metric'])

# Create descriptive filename (without timestamp)
coin_symbols = "_".join(coins.keys())
filename = f"Volatility_TradingRange_365Days_{coin_symbols}.xlsx"
df.to_excel(filename, index=False)
logging.info(f"Data saved to {filename}")

# === Airtable + GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Database"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Upload to GitHub
try:
    github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
    raw_url = github_response['content']['raw_url']
    file_sha = github_response['content']['sha']
    logging.info("File uploaded to GitHub.")

    # Airtable Check
    airtable_headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.get(airtable_url, headers=airtable_headers)
    response.raise_for_status()
    data_airtable = response.json()

    # Check for existing record
    existing_records = [
        rec for rec in data_airtable['records']
        if rec['fields'].get('Name') == "365-Day Volatility and Range"
    ]
    record_id = existing_records[0]['id'] if existing_records else None

    # Upload to Airtable
    if record_id:
        update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
        logging.info("Airtable record updated.")
    else:
        create_airtable_record("365-Day Volatility and Range", raw_url, filename, airtable_url, AIRTABLE_API_KEY)
        logging.info("Airtable record created.")

    # Clean-up
    delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
    os.remove(filename)
    logging.info("File cleaned up from GitHub and local storage.")

except requests.exceptions.RequestException as e:
    logging.error(f"Error in API request: {e}")
except Exception as e:
    logging.error(f"An error occurred: {e}")

logging.info("✅ All done! Airtable attachment replaced and cleanup complete.")

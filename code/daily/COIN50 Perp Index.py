import os
import time
import requests
import pandas as pd
from datetime import datetime
from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
    ensure_utc,
)

# Exact COIN50 weights from the index components table
COIN50_WEIGHTS = {
    'BTC': 0.5085,      # Bitcoin - 50.85%
    'ETH': 0.2220,      # Ethereum - 22.20%
    'XRP': 0.0961,      # XRP - 9.61%
    'SOL': 0.0583,      # Solana - 5.83%
    'DOGE': 0.0200,     # Dogecoin - 2.00%
    'ADA': 0.0172,      # Cardano - 1.72%
    'LINK': 0.0066,     # Chainlink - 0.66%
    'AVAX': 0.0064,     # Avalanche - 0.64%
    'BCH': 0.0060,      # Bitcoin Cash - 0.60%
    'XLM': 0.0060,      # Stellar Lumen - 0.60%
    'SHIB': 0.0054,     # Shiba Inu - 0.54%
    'LTC': 0.0048,      # Litecoin - 0.48%
    'DOT': 0.0046,      # Polkadot - 0.46%
    'PEPE': 0.0036,     # Pepe - 0.36%
    'UNI': 0.0030,      # Uniswap Protocol Token - 0.30%
    'AAVE': 0.0029,     # Aave - 0.29%
    'ICP': 0.0023,      # Internet Computer - 0.23%
    'APT': 0.0022,      # Aptos - 0.22%
    'NEAR': 0.0022,     # Near - 0.22%
    'ETC': 0.0019,      # Ethereum Classic - 0.19%
    'RNDR': 0.0015,     # Render Network - 0.15%
    'FET': 0.0015,      # Artificial Superintelligence Alliance - 0.15%
    'POL': 0.0014,      # Polygon Ecosystem Token - 0.14%
    'QNT': 0.0013,      # Quant - 0.13%
    'ATOM': 0.0012,     # Cosmos - 0.12%
    'ALGO': 0.0012,     # Algorand - 0.12%
    'MKR': 0.0011,      # Maker - 0.11%
    'INJ': 0.0010,      # Injective - 0.10%
    'TIA': 0.0009,      # Celestia - 0.09%
    'BONK': 0.0009,     # BONK - 0.09%
    'STX': 0.0007,      # Stacks - 0.07%
    'CVX': 0.0007,      # Convex Finance - 0.07%
    'GRT': 0.0007,      # The Graph - 0.07%
    'CRV': 0.0007,      # Curve DAO Token - 0.07%
    'LDO': 0.0005,      # Lido DAO - 0.05%
    'JASMY': 0.0005,    # JasmyCoin - 0.05%
    'SAND': 0.0005,     # The Sandbox - 0.05%
    'XTZ': 0.0004,      # Tezos - 0.04%
    'MANA': 0.0004,     # Decentraland - 0.04%
    'HNT': 0.0004,      # Helium - 0.04%
    'APE': 0.0004,      # ApeCoin - 0.04%
    'AERO': 0.0003,     # Aerodrome Finance - 0.03%
    'COMP': 0.0003,     # Compound - 0.03%
    'AXS': 0.0003,      # Axie Infinity Shards - 0.03%
    'CHZ': 0.0003,      # Chiliz - 0.03%
    'AKT': 0.0002,      # Akash Network - 0.02%
    'LPT': 0.0002,      # Livepeer - 0.02%
    '1INCH': 0.0002,    # 1inch - 0.02%
    'SNX': 0.0002,      # Synthetix - 0.02%
    'ROSE': 0.0001,     # Oasis - 0.01%
}

# Complete symbol to CoinGecko ID mapping
SYMBOL_TO_ID = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'XRP': 'ripple',
    'SOL': 'solana',
    'DOGE': 'dogecoin',
    'ADA': 'cardano',
    'LINK': 'chainlink',
    'AVAX': 'avalanche-2',
    'BCH': 'bitcoin-cash',
    'XLM': 'stellar',
    'SHIB': 'shiba-inu',
    'LTC': 'litecoin',
    'DOT': 'polkadot',
    'PEPE': 'pepe',
    'UNI': 'uniswap',
    'AAVE': 'aave',
    'ICP': 'internet-computer',
    'APT': 'aptos',
    'NEAR': 'near',
    'ETC': 'ethereum-classic',
    'RNDR': 'render-token',
    'FET': 'fetch-ai',
    'POL': 'matic-network',  # Polygon
    'QNT': 'quant-network',
    'ATOM': 'cosmos',
    'ALGO': 'algorand',
    'MKR': 'maker',
    'INJ': 'injective-protocol',
    'TIA': 'celestia',
    'BONK': 'bonk',
    'STX': 'blockstack',
    'CVX': 'convex-finance',
    'GRT': 'the-graph',
    'CRV': 'curve-dao-token',
    'LDO': 'lido-dao',
    'JASMY': 'jasmycoin',
    'SAND': 'the-sandbox',
    'XTZ': 'tezos',
    'MANA': 'decentraland',
    'HNT': 'helium',
    'APE': 'apecoin',
    'AERO': 'aerodrome-finance',
    'COMP': 'compound-governance-token',
    'AXS': 'axie-infinity',
    'CHZ': 'chiliz',
    'AKT': 'akash-network',
    'LPT': 'livepeer',
    '1INCH': '1inch',
    'SNX': 'havven',
    'ROSE': 'oasis-network'
}

def get_coin_prices_batch(symbols):
    """Fetch current prices for specified coins from CoinGecko in batches, with robust retry logic"""
    prices = {}
    ids = []
    id_to_symbol = {}
    for symbol in symbols:
        if symbol in SYMBOL_TO_ID:
            coin_id = SYMBOL_TO_ID[symbol]
            ids.append(coin_id)
            id_to_symbol[coin_id] = symbol

    batch_size = 50
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        ids_string = ','.join(batch_ids)
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': ids_string,
            'vs_currencies': 'usd'
        }

        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                for coin_id, price_data in data.items():
                    if coin_id in id_to_symbol and 'usd' in price_data:
                        symbol = id_to_symbol[coin_id]
                        prices[symbol] = price_data['usd']
                break  # Success
            except requests.exceptions.RequestException as e:
                if attempt < max_attempts - 1:
                    time.sleep(2)
                else:
                    print(f"Failed to fetch batch {batch_ids} after {max_attempts} attempts: {e}")
        if i + batch_size < len(ids):
            time.sleep(0.5)
    return prices

def calculate_index_price(weights):
    """Calculate the COIN50 index price based on weights and current prices"""
    symbols = list(weights.keys())
    prices = get_coin_prices_batch(symbols)
    weighted_sum = 0
    for symbol, weight in weights.items():
        if symbol in prices:
            weighted_sum += weight * prices[symbol]
    return weighted_sum

def get_historical_data_since_date(coin_id, start_date):
    """Fetch historical price data for a single coin since a specific date"""
    current_date = datetime.now()
    days_diff = (current_date - start_date).days + 1
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days_diff,
        'interval': 'daily'
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices_data = data['prices']
        df = pd.DataFrame(prices_data, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df[df.index >= start_date]
        return df
    except:
        return None

def calculate_historical_index():
    """Calculate historical COIN50 index values since May 29th, 2025"""
    print("Fetching historical data for COIN50 components since May 29th, 2025...")
    start_date = datetime(2025, 1, 1)  # Use your desired date here
    historical_data = {}
    for symbol, weight in COIN50_WEIGHTS.items():
        if symbol in SYMBOL_TO_ID:
            coin_id = SYMBOL_TO_ID[symbol]
            print(f"Fetching data for {symbol}...")
            df = get_historical_data_since_date(coin_id, start_date)
            if df is not None:
                historical_data[symbol] = df
            time.sleep(0.5)
    print("Processing historical index values...")
    all_dates = None
    for symbol, df in historical_data.items():
        if all_dates is None:
            all_dates = set(df.index.date)
        else:
            all_dates = all_dates.intersection(set(df.index.date))
    common_dates = sorted(list(all_dates))
    index_values = []
    dates = []
    for date in common_dates:
        daily_weighted_sum = 0
        total_weight = 0
        for symbol, weight in COIN50_WEIGHTS.items():
            if symbol in historical_data:
                df = historical_data[symbol]
                date_data = df[df.index.date == date]
                if not date_data.empty:
                    price = date_data['price'].iloc[0]
                    daily_weighted_sum += weight * price
                    total_weight += weight
        if total_weight > 0.8:
            final_value = daily_weighted_sum / 131.37
            index_values.append(final_value)
            dates.append(date)
    index_df = pd.DataFrame({
        'date': dates,
        'index_value': index_values
    })
    index_df['date'] = pd.to_datetime(index_df['date'])
    index_df.set_index('date', inplace=True)
    return index_df

# === Generate index values ===
index_df = calculate_historical_index()
index_df = ensure_utc(index_df)

# === Save to Excel (fix: ensure date is in file as column) ===
index_df.reset_index().to_excel('coin50_perp_index_daily.xlsx', index=False)
filename = 'coin50_perp_index_daily.xlsx'

# === Airtable/GitHub Config ===
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = 'appnssPRD9yeYJJe5'
TABLE_NAME = 'daily'
airtable_url = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}'
GITHUB_REPO = 'SagarFieldElevate/DatabaseManagement'
BRANCH = 'main'
UPLOAD_PATH = 'Uploads'
GITHUB_TOKEN = os.getenv('GH_TOKEN')

# === Upload to GitHub (fix: check for 'content' key) ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
if "content" not in github_response:
    raise Exception("GitHub upload failed: missing 'content' in response.")
raw_url = github_response["content"]["raw_url"]  # <-- FIXED: Use 'raw_url' not 'download_url'
file_sha = github_response["content"]["sha"]

# === Check Airtable for existing record ===
airtable_headers = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json',
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records = response.json().get('records', [])
existing = [rec for rec in records if rec['fields'].get('Name') == 'COIN50 Perp Index Daily']
record_id = existing[0]['id'] if existing else None

# === Update or create record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record('COIN50 Perp Index Daily', raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print('✅ COIN50 Perp Index Daily uploaded to Airtable and GitHub cleaned up.')

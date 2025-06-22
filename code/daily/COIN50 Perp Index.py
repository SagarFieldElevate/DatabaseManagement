from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
import time
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Initialize CoinGecko ===
cg = CoinGeckoAPI()

# === Define COIN50 weights and coin mappings ===
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
    'POL': 'matic-network',
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

# === Set date range ===
start_date = datetime(2015, 1, 1)
current_date = datetime.now()
days_since_start = (current_date - start_date).days + 1

# === Fetch only recent data (last 365 days) for faster processing ===
print("Fetching COIN50 historical data for the last 365 days...")
historical_data = {}

# Process coins in batches to reduce API calls
batch_size = 10
symbols_list = list(COIN50_WEIGHTS.keys())

for i in range(0, len(symbols_list), batch_size):
    batch_symbols = symbols_list[i:i + batch_size]
    
    for symbol in batch_symbols:
        if symbol in SYMBOL_TO_ID:
            coin_id = SYMBOL_TO_ID[symbol]
            print(f"Fetching data for {symbol}...")
            
            try:
                # Fetch only last 365 days to reduce processing time
                market_data = cg.get_coin_market_chart_by_id(
                    id=coin_id, 
                    vs_currency='usd', 
                    days=365,
                    interval='daily'
                )
                
                # Convert to DataFrame
                price_data = market_data['prices']
                df = pd.DataFrame(price_data, columns=['timestamp', 'price'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                historical_data[symbol] = df
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                continue
    
    # Small delay between batches
    if i + batch_size < len(symbols_list):
        time.sleep(0.5)

# === Calculate COIN50 index values ===
print("Calculating COIN50 index values...")

# Find common dates across all coins
all_dates = None
for symbol, df in historical_data.items():
    if all_dates is None:
        all_dates = set(df.index.date)
    else:
        all_dates = all_dates.intersection(set(df.index.date))

# Convert to sorted list
common_dates = sorted(list(all_dates))

# Calculate index value for each date
index_data = []

for date in common_dates:
    daily_weighted_sum = 0
    total_weight = 0
    
    for symbol, weight in COIN50_WEIGHTS.items():
        if symbol in historical_data:
            df = historical_data[symbol]
            # Get price for this date
            date_data = df[df.index.date == date]
            if not date_data.empty:
                price = date_data['price'].iloc[0]
                daily_weighted_sum += weight * price
                total_weight += weight
    
    # Only add if we have data for most of the index
    if total_weight > 0.8:  # At least 80% of weights represented
        # Apply the divisor
        index_value = daily_weighted_sum / 131.37
        
        index_data.append({
            'Date': date.strftime('%Y-%m-%d'),
            'COIN50 Index Value': round(index_value, 2)
        })

# === Create DataFrame with only Date and Index Value ===
index_df = pd.DataFrame(index_data)

# === Calculate current index value ===
print("Calculating current COIN50 index value...")
current_prices = {}
coin_ids = list(SYMBOL_TO_ID.values())

# Get current prices in one batch call
try:
    # CoinGecko allows up to 250 IDs per call
    ids_string = ','.join(coin_ids)
    prices_data = cg.get_price(ids=ids_string, vs_currencies='usd')
    current_prices = prices_data
except Exception as e:
    print(f"Error fetching current prices: {e}")
    # Fallback to batch approach if single call fails
    for i in range(0, len(coin_ids), 50):
        batch_ids = coin_ids[i:i + 50]
        try:
            prices_data = cg.get_price(ids=','.join(batch_ids), vs_currencies='usd')
            current_prices.update(prices_data)
        except:
            pass

# Calculate current index
current_weighted_sum = 0
for symbol, weight in COIN50_WEIGHTS.items():
    if symbol in SYMBOL_TO_ID:
        coin_id = SYMBOL_TO_ID[symbol]
        if coin_id in current_prices and 'usd' in current_prices[coin_id]:
            price = current_prices[coin_id]['usd']
            current_weighted_sum += weight * price

current_index_value = current_weighted_sum / 131.37

# Add current value to DataFrame if not already included
current_date_str = datetime.now().strftime('%Y-%m-%d')
if index_df.empty or index_df['Date'].iloc[-1] != current_date_str:
    current_data = {
        'Date': current_date_str,
        'COIN50 Index Value': round(current_index_value, 2)
    }
    index_df = pd.concat([index_df, pd.DataFrame([current_data])], ignore_index=True)

# === Save to Excel ===
filename = "coin50_index_historical.xlsx"
index_df = ensure_utc(index_df)
index_df.to_excel(filename, index=False)

print(f"✅ COIN50 Index data saved to {filename}")
print(f"Total data points: {len(index_df)}")
print(f"Date range: {index_df['Date'].iloc[0]} to {index_df['Date'].iloc[-1]}")
print(f"Current index value: {current_index_value:.2f}")

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
    if rec['fields'].get('Name') == "COIN50 Perpetual Index (365 Days)"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Update or create Airtable record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("COIN50 Perpetual Index (365 Days)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Clean-up ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ COIN50 index data uploaded to GitHub, Airtable updated, and files cleaned up.")

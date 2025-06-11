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

# === COIN50 Index Weights ===
COIN50_WEIGHTS = {
    'BTC': 0.5085,
    'ETH': 0.2220,
    'XRP': 0.0961,
    'SOL': 0.0583,
    'DOGE': 0.0200,
    'ADA': 0.0172,
    'LINK': 0.0066,
    'AVAX': 0.0064,
    'BCH': 0.0060,
    'XLM': 0.0060,
    'SHIB': 0.0054,
    'LTC': 0.0048,
    'DOT': 0.0046,
    'PEPE': 0.0036,
    'UNI': 0.0030,
    'AAVE': 0.0029,
    'ICP': 0.0023,
    'APT': 0.0022,
    'NEAR': 0.0022,
    'ETC': 0.0019,
    'RNDR': 0.0015,
    'FET': 0.0015,
    'POL': 0.0014,
    'QNT': 0.0013,
    'ATOM': 0.0012,
    'ALGO': 0.0012,
    'MKR': 0.0011,
    'INJ': 0.0010,
    'TIA': 0.0009,
    'BONK': 0.0009,
    'STX': 0.0007,
    'CVX': 0.0007,
    'GRT': 0.0007,
    'CRV': 0.0007,
    'LDO': 0.0005,
    'JASMY': 0.0005,
    'SAND': 0.0005,
    'XTZ': 0.0004,
    'MANA': 0.0004,
    'HNT': 0.0004,
    'APE': 0.0004,
    'AERO': 0.0003,
    'COMP': 0.0003,
    'AXS': 0.0003,
    'CHZ': 0.0003,
    'AKT': 0.0002,
    'LPT': 0.0002,
    '1INCH': 0.0002,
    'SNX': 0.0002,
    'ROSE': 0.0001,
}

# === Symbol to CoinGecko ID mapping ===
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
    'ROSE': 'oasis-network',
}


def get_historical_data_since_date(coin_id: str, start_date: datetime) -> pd.DataFrame | None:
    """Fetch daily price data for a coin from CoinGecko starting at start_date."""
    days = (datetime.utcnow() - start_date).days + 1
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily',
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('Date', inplace=True)
        df.drop(columns=['timestamp'], inplace=True)
        return df[df.index >= start_date]
    except Exception:
        return None


def calculate_historical_index() -> pd.DataFrame:
    """Calculate COIN50 index values from January 1, 2025 to today."""
    start_date = datetime(2025, 1, 1)
    historical = {}
    for symbol in COIN50_WEIGHTS:
        coin_id = SYMBOL_TO_ID.get(symbol)
        if not coin_id:
            continue
        df = get_historical_data_since_date(coin_id, start_date)
        if df is not None:
            historical[symbol] = df
        time.sleep(0.5)

    all_dates = None
    for df in historical.values():
        if all_dates is None:
            all_dates = set(df.index.date)
        else:
            all_dates &= set(df.index.date)
    if not all_dates:
        return pd.DataFrame(columns=['Date', 'COIN50 Perp Index Value'])

    dates = sorted(all_dates)
    records = []
    for date in dates:
        weighted_sum = 0
        total_weight = 0
        for symbol, weight in COIN50_WEIGHTS.items():
            df = historical.get(symbol)
            if df is None:
                continue
            day_data = df[df.index.date == date]
            if not day_data.empty:
                price = day_data['price'].iloc[0]
                weighted_sum += weight * price
                total_weight += weight
        if total_weight > 0:
            records.append({
                'Date': pd.to_datetime(date, utc=True),
                'COIN50 Perp Index Value': weighted_sum / 131.37,
            })

    index_df = pd.DataFrame(records).sort_values('Date')
    return index_df


# === Generate index values ===
index_df = calculate_historical_index()
index_df = ensure_utc(index_df)

# === Save to Excel ===
filename = 'coin50_perp_index_daily.xlsx'
index_df.to_excel(filename, index=False)

# === Airtable/GitHub Config ===
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = 'appnssPRD9yeYJJe5'
TABLE_NAME = 'daily'
airtable_url = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}'

GITHUB_REPO = 'SagarFieldElevate/DatabaseManagement'
BRANCH = 'main'
UPLOAD_PATH = 'Uploads'
GITHUB_TOKEN = os.getenv('GH_TOKEN')

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

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

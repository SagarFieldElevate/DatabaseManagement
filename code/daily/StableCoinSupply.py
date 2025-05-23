import requests
import pandas as pd
from datetime import datetime
import os
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

# List of stablecoins and their DefiLlama IDs
stablecoins = {
    'USDT': '1',
    'USDC': '2',
    'DAI': '3',
    'BUSD': '4',
    'TUSD': '5',
    'PAX': '6'
}

# Function to fetch data for each stablecoin
def fetch_stablecoin_by_id(stablecoin_id: str, symbol_hint=''):
    url = f"https://stablecoins.llama.fi/stablecoin/{stablecoin_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    name = data.get("name", f"Stablecoin_{stablecoin_id}")
    chain_balances = data.get("chainBalances", {})

    records = []

    for chain, entries in chain_balances.items():
        for entry in entries.get("tokens", []):
            date_ts = entry.get("date")
            if not date_ts:
                continue

            date = datetime.utcfromtimestamp(date_ts).date()
            circulating = entry.get("circulating", {}).get("peggedUSD", 0)

            records.append({
                "date": date,
                "symbol": symbol_hint or data.get("symbol", name),
                "chain": chain,
                "circulating_usd": circulating
            })

    df = pd.DataFrame(records)
    return df

# Fetch and merge data for each stablecoin
df_all_stablecoins = pd.DataFrame()

for coin, coin_id in stablecoins.items():
    coin_df = fetch_stablecoin_by_id(coin_id, symbol_hint=coin)
    df_all_stablecoins = pd.concat([df_all_stablecoins, coin_df])

# Group by date and symbol, then sum across stablecoins
df_grouped = df_all_stablecoins.groupby(['date', 'symbol'])['circulating_usd'].sum().reset_index()

# Add a column for the sum of circulating supply across all stablecoins
df_grouped['total_circulating_usd'] = df_grouped.groupby('date')['circulating_usd'].transform('sum')

# Pivot the data for easier plotting
df_pivoted = df_grouped.pivot(index='date', columns='symbol', values='circulating_usd')

# Add the total circulating supply to the pivoted dataframe
df_pivoted['Total'] = df_grouped.groupby('date')['total_circulating_usd'].first()

# Save the data to Excel file
filename = "stablecoin_circulating_supply_with_sum.xlsx"
df_pivoted = ensure_utc(df_pivoted)
df_pivoted.to_excel(filename)

# Upload to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# Airtable Check
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "Stablecoin Circulating Supply"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Stablecoin Circulating Supply", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)

print("✅ Stablecoin Circulating Supply with Total: Airtable updated and GitHub cleaned up.")

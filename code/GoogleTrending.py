from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# Initialize CoinGecko
cg = CoinGeckoAPI()

# Fetch trending coins from CoinGecko
print("🔍 Fetching trending coins from CoinGecko...")
trending_data = cg.get_search_trending()

# Prepare the data
coin_list = []
for coin_info in trending_data['coins']:
    coin = coin_info.get('item', {})
    coin_list.append({
        'Name': coin.get('name'),
        'Symbol': coin.get('symbol'),
        'ID': coin.get('id'),
        'Market Cap Rank': coin.get('market_cap_rank'),
        'Score': coin.get('score'),
    })

# Create DataFrame and export to Excel
df = pd.DataFrame(coin_list)
df['Date'] = datetime.now().strftime("%Y-%m-%d")
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"trending_coins_{timestamp}.xlsx"
df.to_excel(filename, index=False)

# === Airtable + GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"  # Replace with your actual Airtable Base ID
TABLE_NAME = "Database"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"  # Replace with your actual GitHub repository
BRANCH = "main"
UPLOAD_PATH = "uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Upload to GitHub
print("📤 Uploading file to GitHub...")
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
    if rec['fields'].get('Name') == "Trending Coins"
]
record_id = existing_records[0]['id'] if existing_records else None

# Always replace attachment — either update or create
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Trending Coins", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Clean-up
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ All done! Airtable attachment replaced and cleanup complete.")

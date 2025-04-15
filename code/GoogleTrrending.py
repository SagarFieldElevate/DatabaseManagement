import requests
import pandas as pd
from datetime import datetime, timezone
import base64
import os
from data_upload_utils import upload_to_github, create_airtable_record, delete_file_from_github

# ======== CONFIG ========
BRANCH = "main"
GITHUB_REPO = "SagarFieldElevate/Trial"
UPLOAD_PATH = "uploads"

# Pull secrets from GitHub Actions
GITHUB_TOKEN = os.getenv("GH_TOKEN")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appFww2fieWK3mKwi"
TABLE_NAME = "Database"

# === Fetch trending coins from CoinGecko ===
print("🔍 Fetching trending coins from CoinGecko...")
url = "https://api.coingecko.com/api/v3/search/trending"
resp = requests.get(url)
resp.raise_for_status()
trending_data = resp.json().get("coins", [])

# === Prepare data for DataFrame ===
coin_list = []
for coin_info in trending_data:
    coin = coin_info.get("item", {})
    data = coin.get("data", {})
    price_change_24h = data.get("price_change_percentage_24h", {})

    coin_list.append({
        "Name": coin.get("name"),
        "Symbol": coin.get("symbol"),
        "ID": coin.get("id"),
        "Market Cap Rank": coin.get("market_cap_rank"),
        "Price (BTC)": coin.get("price_btc"),
        "Score": coin.get("score"),
        "Total Volume": data.get("total_volume"),
        "24h Change (%) USD": price_change_24h.get("usd"),
    })

df = pd.DataFrame(coin_list)

# === Save to Excel ===
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
filename = f"trending_coins_{timestamp}.xlsx"
df.to_excel(filename, index=False)

# === Upload to GitHub ===
print("📤 Uploading file to GitHub...")
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Send to Airtable ===
print("📬 Sending GitHub file URL to Airtable...")
create_airtable_record(timestamp, raw_url, filename, BASE_ID, TABLE_NAME, AIRTABLE_API_KEY)

# === Delete file from GitHub ===
print("🧹 Deleting file from GitHub...")
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)

# === Delete local file ===
os.remove(filename)
print("🧽 Local file deleted.")
print("✅ Workflow complete.")

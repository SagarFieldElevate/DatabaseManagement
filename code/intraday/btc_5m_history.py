import pandas as pd
import requests
import os
import time
from datetime import datetime
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "intraday"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

# === Fetch Binance BTC 5m Data Function ===
def get_binance_us_btc_5m_history(days=140):
    url = "https://api.binance.us/api/v3/klines"
    interval = "5m"
    limit = 1000
    symbol = "BTCUSDT"

    all_data = []
    end_time = int(time.time() * 1000)  # current time in ms

    # Loop back 140 days in 1000-candle chunks
    for _ in range((days * 288) // limit + 1):
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "endTime": end_time
        }

        response = requests.get(url, params=params)
        data = response.json()

        if isinstance(data, dict) and data.get("code"):
            print("Error:", data["msg"])
            break

        if not data:
            break

        all_data = data + all_data  # prepend to keep chronological order
        end_time = data[0][0] - 1  # move back before earliest timestamp

        time.sleep(0.5)  # avoid rate limit

    # Build DataFrame
    df = pd.DataFrame(all_data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df.rename(columns={"open_time": "Date"}, inplace=True)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d %H:%M")
    return df

# === Main Script ===
btc_df = get_binance_us_btc_5m_history(140)
filename = "binance_btc_5m_history.xlsx"
btc_df = ensure_utc(btc_df)
btc_df.to_excel(filename, index=False)

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
    if rec['fields'].get('Name') == "Binance BTC 5m History"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Binance BTC 5m History", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Binance BTC 5m History: Airtable updated and GitHub cleaned up.")

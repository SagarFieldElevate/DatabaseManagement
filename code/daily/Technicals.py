import os
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Fetch BTC-USD Data with Indicators ===
df = yf.download("BTC-USD", start="2015-01-01", progress=False)

# Clean column names
if isinstance(df.columns[0], tuple):
    df.columns = ['_'.join(col).lower() for col in df.columns]
else:
    df.columns = [col.lower() for col in df.columns]

df.dropna(inplace=True)

# Add technical indicators
df.ta.ema(length=20, append=True)
df.ta.ema(length=8, append=True)
df.ta.rsi(length=14, append=True)
df.ta.macd(append=True)

# Reset index to make 'Date' a column
df.reset_index(inplace=True)

# Optional: Rename columns for clarity (example)
df.rename(columns={
    'date': 'Date',
    'close': 'Close',
    'high': 'High',
    'low': 'Low',
    'open': 'Open',
    'volume': 'Volume',
    'EMA_20': 'EMA 20',
    'EMA_8': 'EMA 8',
    'RSI_14': 'RSI 14',
    'MACD_12_26_9': 'MACD Line',
    'MACDh_12_26_9': 'MACD Histogram',
    'MACDs_12_26_9': 'MACD Signal'
}, inplace=True)

# === Save to Excel ===
filename = "bitcoin_technical_indicators.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['download_url']
file_sha = github_response['content']['sha']

# === Airtable Check ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records = response.json()["records"]

existing_records = [
    rec for rec in records
    if rec['fields'].get('Name') == "Bitcoin Technical Indicators"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Upload to Airtable ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Bitcoin Technical Indicators", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Bitcoin Technical Indicators: Airtable updated and GitHub cleaned up.")

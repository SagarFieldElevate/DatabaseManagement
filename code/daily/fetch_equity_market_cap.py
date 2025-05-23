import pandas as pd
from datetime import datetime
import os
import yfinance as yf
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

# === Indicator Fetch Function ===
def get_equity_market_cap_daily(start_date="2015-01-01"):
    ticker = "^W5000"
    data = yf.download(ticker, start=start_date, interval="1d")
    data = data.reset_index()[['Date', 'Close']]
    data.dropna(inplace=True)
    data.rename(columns={'Close': 'US Equity Market Capitalization (Billions USD)'}, inplace=True)
    data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
    data['US Equity Market Capitalization (Billions USD)'] = data['US Equity Market Capitalization (Billions USD)'].round(2)
    return data

# === Main Script ===
df = get_equity_market_cap_daily(start_date="2015-01-01")
# Flatten MultiIndex columns if necessary
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [' '.join(col).strip() for col in df.columns]

# Sanitize any column names that accidentally include the ticker
df.columns = [col.replace("^W5000", "").strip() for col in df.columns]
filename = "equity_market_cap_daily.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# Upload to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# Check existing Airtable record
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "US Equity Market Capitalization (Billions USD)"
]
record_id = existing_records[0]['id'] if existing_records else None

# Update or create Airtable record
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("US Equity Market Capitalization (Billions USD)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ US Equity Market Capitalization (Billions USD) — Daily: Airtable updated and GitHub cleaned up.")

import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "monthly"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

def get_dividend_yield_from_csv(file_path, start_date="2015-01-01"):
    df = pd.read_csv(file_path)

    # Rename the 'time' column to 'Date' to match the expected column name
    df.rename(columns={'time': 'Date'}, inplace=True)

    # Attempt to auto-detect the 'value' column (which should be 'close' in your case)
    value_col = 'close'

    df = df[['Date', value_col]].rename(columns={
        'Date': 'Date',
        value_col: 'S&P 500 Dividend Yield (%)'
    })

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    df = df[df['Date'] >= pd.to_datetime(start_date)]
    df = df[df['Date'] <= datetime.now()]
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    df['S&P 500 Dividend Yield (%)'] = pd.to_numeric(df['S&P 500 Dividend Yield (%)'], errors='coerce').round(2)
    df = df.dropna()

    return df

# === Main Script ===
local_file_path = "uploads/MULTPL_SP500_DIV_YIELD_MONTH, 1D.csv"
df = get_dividend_yield_from_csv(local_file_path, start_date="2015-01-01")
filename = "sp500_dividend_yield.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# === GitHub Upload ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Airtable Update/Create ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "S&P 500 Dividend Yield (%)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("S&P 500 Dividend Yield (%)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ S&P 500 Dividend Yield (%): Airtable updated and GitHub cleaned up.")

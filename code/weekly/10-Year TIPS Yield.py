import pandas as pd
from datetime import datetime
import os
import requests
import time
from fredapi import Fred
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "weekly"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Helper: FRED fetch with retries ===
def fetch_series(series_id, start_date, max_retries=5, backoff=1.0):
    for attempt in range(max_retries):
        try:
            return fred.get_series(series_id, start_date=start_date)
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise

# === Indicator Fetch Function ===
def get_tips_yield(start_date="2015-01-01"):
    data = fetch_series('DFII10', start_date)
    df = pd.DataFrame({
        'Date': data.index,
        '10-Year TIPS Yield (%)': data.values
    })
    df['Date'] = pd.to_datetime(df['Date'])
    current_date = datetime.utcnow()
    df = df[df['Date'] <= current_date]
    df = df.set_index('Date').resample('W').mean().reset_index()
    df['10-Year TIPS Yield (%)'] = df['10-Year TIPS Yield (%)'].round(2)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    return df

# === Main Script ===
df = get_tips_yield()
filename = "10_year_tips_yield_weekly.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "10-Year TIPS Yield (%)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("10-Year TIPS Yield (%)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ 10-Year TIPS Yield (%): Airtable updated and GitHub cleaned up.")

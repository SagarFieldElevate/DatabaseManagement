import pandas as pd
from datetime import datetime
import os
import requests
from fredapi import Fred
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")  # <-- Add your FRED API key to GitHub Secrets
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Financial Market Indicators"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_dividend_yields(start_date="2015-01-01"):
    fred = Fred(api_key=FRED_API_KEY)
    series = fred.get_series("SP500DY")
    df = series.reset_index()
    df.columns = ['Date', 'S&P 500 Dividend Yield (%)']
    
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df = df[df['Date'] >= start_date]
    df['S&P 500 Dividend Yield (%)'] = df['S&P 500 Dividend Yield (%)'].round(2)
    
    return df

# === Main Script ===
df = get_dividend_yields(start_date="2015-01-01")
filename = "sp500_dividend_yield.xlsx"
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
    if rec['fields'].get('Name') == "S&P 500 Dividend Yield (%)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("S&P 500 Dividend Yield (%)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ S&P 500 Dividend Yield (%): Airtable updated and GitHub cleaned up.")

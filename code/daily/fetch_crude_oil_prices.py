import pandas as pd
from datetime import datetime
import os
import requests
import yfinance as yf
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
def get_crude_oil_prices(start_date="2015-01-01"):
    ticker = yf.Ticker("CL=F")
    data = ticker.history(start=start_date, end=datetime.now().strftime('%Y-%m-%d'))
    df = pd.DataFrame({
        'Date': data.index,
        'WTI Crude Oil Price (USD/Barrel)': data['Close']
    })
    
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    df['WTI Crude Oil Price (USD/Barrel)'] = df['WTI Crude Oil Price (USD/Barrel)'].round(2)
    
    return df

# === Main Script ===
df = get_crude_oil_prices(start_date="2015-01-01")
filename = "wti_crude_oil_prices.xlsx"
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
    if rec['fields'].get('Name') == "WTI Crude Oil Price (USD/Barrel)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("WTI Crude Oil Price (USD/Barrel)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ WTI Crude Oil Price (USD/Barrel): Airtable updated and GitHub cleaned up.")
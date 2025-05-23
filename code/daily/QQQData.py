import os
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
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

symbol = "QQQ"
indicator_name = "QQQ Daily Close Price"

# === Fetch QQQ Close Price Data (from Jan 1, 2015) ===
def get_qqq_close_data(start_date="2015-01-01"):
    # Download data from Yahoo Finance
    df = yf.download(symbol, start=start_date)[['Close']].reset_index()
    print(f"Fetched data for {symbol}: {df.shape[0]} rows")  # Debug line
    df.columns = ['Date', 'QQQ Close Price (USD)']
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df['QQQ Close Price (USD)'] = df['QQQ Close Price (USD)'].round(2)
    print(f"Data after formatting: {df.head()}")  # Debug line
    return df

# === Main Script ===
df = get_qqq_close_data(start_date="2015-01-01")

if df.empty:
    print("Warning: The dataframe is empty. Check if the data was fetched correctly.")
else:
    print(f"Saving {df.shape[0]} rows to Excel file.")
    filename = "qqq_daily_close_price.xlsx"
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
        if rec['fields'].get('Name') == indicator_name
    ]
    record_id = existing_records[0]['id'] if existing_records else None

    # === Upload to Airtable ===
    if record_id:
        update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
    else:
        create_airtable_record(indicator_name, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

    # === Cleanup ===
    delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
    os.remove(filename)
    print(f"✅ {indicator_name}: Airtable updated and GitHub cleaned up.")

import pandas as pd
from datetime import datetime
import os
import requests
from fredapi import Fred
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_currency_exchange():
    start_date = "2015-01-01"
    cny = fred.get_series('DEXCHUS', start_date=start_date)
    eur = fred.get_series('DEXUSEU', start_date=start_date)
    jpy = fred.get_series('DEXJPUS', start_date=start_date)
    
    # Create DataFrame
    df = pd.DataFrame({
        'Date': cny.index,
        'USD to CNY Exchange Rate': cny.values,
        'USD to EUR Exchange Rate': eur.reindex(cny.index).values,
        'USD to JPY Exchange Rate': jpy.reindex(cny.index).values
    })
    
    # Convert 'Date' to date-only string format
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    
    # Filter data from 2015 to the current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    
    # Round exchange rates to 4 decimal places
    df['USD to CNY Exchange Rate'] = df['USD to CNY Exchange Rate'].round(4)
    df['USD to EUR Exchange Rate'] = df['USD to EUR Exchange Rate'].round(4)
    df['USD to JPY Exchange Rate'] = df['USD to JPY Exchange Rate'].round(4)
    
    return df

# === Main Script ===
df = get_currency_exchange()
filename = "usd_currency_exchange_rates.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

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
    if rec['fields'].get('Name') == "USD Currency Exchange Rates"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("USD Currency Exchange Rates", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ USD Currency Exchange Rates: Airtable updated and GitHub cleaned up.")

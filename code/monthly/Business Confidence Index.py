import pandas as pd
from datetime import datetime
import os
import requests
from pandas_datareader import data as pdr
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

# === Indicator Fetch Function ===
def get_business_confidence(start_date="2015-01-01"):
    # Fetch OECD Business Confidence Index (BCI) for the US
    data = pdr.get_data_oecd('BCI.USA.M')  # Business Confidence Index, USA, Monthly
    df = pd.DataFrame({
        'Date': data.index,
        'US Business Confidence Index': data['Value']
    })
    
    # Convert 'Date' to date-only string format
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    
    # Filter data from 2015 to today
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] >= start_date]
    df = df[df['Date'] <= current_date]
    
    # Round values to 2 decimal places
    df['US Business Confidence Index'] = df['US Business Confidence Index'].round(2)
    
    return df

# === Main Script ===
df = get_business_confidence(start_date="2015-01-01")
filename = "us_business_confidence.xlsx"
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
    if rec['fields'].get('Name') == "US Business Confidence Index"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("US Business Confidence Index", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ US Business Confidence Index: Airtable updated and GitHub cleaned up.")

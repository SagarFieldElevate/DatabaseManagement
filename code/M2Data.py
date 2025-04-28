import pandas as pd
from datetime import datetime
import os
import requests
from fredapi import Fred
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Database"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

# === Fetch US M2 Data ===
def get_us_m2(start_date="2015-01-01"):
    data = fred.get_series('M2SL', start_date=start_date)
    df = pd.DataFrame({
        'Date': data.index.strftime('%Y-%m-%d'),  # Capitalized 'Date'
        'us_m2': data.values
    })
    return df

df = get_us_m2(start_date="2015-01-01")

# === Save to Excel ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"US_M2_{timestamp}.xlsx"
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
    if rec['fields'].get('Name') == "US M2 Money Supply"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Upload to Airtable ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("US M2 Money Supply", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ US M2 Money Supply: Airtable updated and GitHub cleaned up.")

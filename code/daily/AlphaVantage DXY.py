import os
import requests
import pandas as pd
from datetime import datetime
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "BDLHVHE5630WUQQC")
url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=DXY&apikey={API_KEY}&outputsize=full"
response = requests.get(url)
response.raise_for_status()
data = response.json().get("Time Series (Daily)", {})

records = []
for date_str, values in data.items():
    records.append({
        "Date": date_str,
        "DXY Close Price (USD)": float(values["4. close"])
    })
records.sort(key=lambda x: x["Date"])

# === Save to Excel ===
df = pd.DataFrame(records)
filename = "alphavantage_dxy_daily.xlsx"
df.to_excel(filename, index=False)

# === Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "AlphaVantage DXY Daily Close"

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Check if record exists ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records_airtable = response.json().get('records', [])
existing_records = [rec for rec in records_airtable if rec['fields'].get('Name') == INDICATOR_NAME]
record_id = existing_records[0]['id'] if existing_records else None

# === Update or create record ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ AlphaVantage DXY data uploaded to Airtable and GitHub cleaned up.")

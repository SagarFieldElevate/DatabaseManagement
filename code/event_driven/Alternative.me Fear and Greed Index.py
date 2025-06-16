import os
import requests
import pandas as pd
from datetime import datetime
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Fetch Fear & Greed Index ===
response = requests.get("https://api.alternative.me/fng/?format=json&limit=730")
response.raise_for_status()
entries = response.json().get("data", [])

records = []
for entry in entries:
    date = datetime.utcfromtimestamp(int(entry["timestamp"])).strftime("%Y-%m-%d")
    records.append({
        "Date": date,
        "Fear & Greed Index": int(entry["value"]),
        "Classification": entry["value_classification"],
    })

# === Save to Excel ===
df = pd.DataFrame(records)
filename = "fear_greed_index.xlsx"
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
INDICATOR_NAME = "Fear & Greed Index"

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Check if record exists in Airtable ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records_airtable = response.json().get("records", [])
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
print("✅ Fear & Greed Index uploaded to Airtable and GitHub cleaned up.")

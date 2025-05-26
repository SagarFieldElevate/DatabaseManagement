import pandas as pd
import os
import requests
from dune_client.client import DuneClient
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
dune = DuneClient("63revqtmAaY9OoFIRoudipI7wN4NQLAL")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Fetch BTC ETF Net Flow Data from Dune ===
query_id = 5073067
query_result = dune.get_latest_result(query_id)
df = pd.DataFrame(query_result.result.rows)
time_col = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()][0]
df.rename(columns={time_col: 'Date'}, inplace=True)
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

filename = "btc_etf_net_flow.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['download_url']
file_sha = github_response['content']['sha']

# === Airtable Setup ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

# Check if record exists
existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "BTC ETF Net Flow"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Upload to Airtable ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("BTC ETF Net Flow", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ BTC ETF Net Flow: Airtable updated and GitHub cleaned up.")

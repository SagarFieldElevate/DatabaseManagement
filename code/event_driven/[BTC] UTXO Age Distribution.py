import pandas as pd
import os
import requests
from dune_client.client import DuneClient
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
dune = DuneClient()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "event_driven"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Fetch [BTC] UTXO Age Distribution ===
query_id = 5130650
query_result = dune.get_latest_result(query_id)
df = pd.DataFrame(query_result.result.rows)
time_col = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()][0]
df.rename(columns={time_col: 'Date'}, inplace=True)
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

filename = "btc_utxo_age_distribution.xlsx"
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

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "[BTC] UTXO Age Distribution"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Upload to Airtable ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("[BTC] UTXO Age Distribution", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ [BTC] UTXO Age Distribution: Airtable updated and GitHub cleaned up.")

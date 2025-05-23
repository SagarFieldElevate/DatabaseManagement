import os
import pandas as pd
import requests
from dune_client.client import DuneClient
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

INDICATOR_NAME = "Bitcoin Exchange Net Flows"
QUERY_ID = 123456  # Dune query for BTC exchange net flows


def fetch_dune_series(query_id: int) -> pd.DataFrame:
    dune = DuneClient()
    query_result = dune.get_latest_result(query_id)
    df = pd.DataFrame(query_result.result.rows)
    time_col = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()][0]
    value_col = [c for c in df.columns if c != time_col][0]
    df.rename(columns={time_col: "Date", value_col: INDICATOR_NAME}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    return df


# === Main Script ===

df = fetch_dune_series(QUERY_ID)

filename = "bitcoin_exchange_net_flows.xlsx"
df.to_excel(filename, index=False)

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
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
    if rec['fields'].get('Name') == INDICATOR_NAME
]
record_id = existing_records[0]['id'] if existing_records else None

# === Upload to Airtable ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print(f"✅ {INDICATOR_NAME}: Airtable updated and GitHub cleaned up.")

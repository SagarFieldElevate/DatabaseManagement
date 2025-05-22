import os
import pandas as pd
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
GLASSNODE_API_KEY = os.getenv("GLASSNODE_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

INDICATOR_NAME = "Ethereum Miner Outflows"
ENDPOINT = "/v1/metrics/transactions/miner_outflows"


def fetch_glassnode_series(asset: str) -> pd.DataFrame:
    url = f"https://api.glassnode.com{ENDPOINT}"
    params = {"a": asset, "api_key": GLASSNODE_API_KEY}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data)
    df["t"] = pd.to_datetime(df["t"], unit="s").dt.strftime("%Y-%m-%d")
    df.columns = ["Date", INDICATOR_NAME]
    return df


# === Main Script ===
df = fetch_glassnode_series("ETH")
filename = "ethereum_miner_outflows.xlsx"
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

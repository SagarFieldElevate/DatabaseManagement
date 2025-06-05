import os
import requests
import pandas as pd
from datetime import datetime
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

API_KEY = os.getenv("ETHERSCAN_API_KEY", "R1C32K1CWPMNJFWWNFIA51QGPSNRAAEBRJ")
ADDRESS = os.getenv("ETHERSCAN_ADDRESS", "0xdAC17F958D2ee523a2206206994597C13D831ec7")

# Fetch maximum 10,000 records
resp = requests.get(f"https://api.etherscan.io/api?module=account&action=tokentx&address={ADDRESS}&page=1&offset=10000&sort=desc&apikey={API_KEY}")
resp.raise_for_status()
items = resp.json().get("result", [])

records = []
for item in items:
    # Convert Unix timestamp to readable date
    timestamp = int(item.get("timeStamp", 0))
    date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    records.append({
        "Date": date,  # Date as first column
        "TxHash": item.get("hash"),
        "Value": item.get("value"),
        "Token": item.get("tokenSymbol"),
    })

df = pd.DataFrame(records)
filename = "etherscan_token_events.xlsx"
df.to_excel(filename, index=False)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "event_driven"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "Etherscan Token Events"

res = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = res["content"]["raw_url"]
file_sha = res["content"]["sha"]

airtable_headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
response = requests.get(airtable_url, headers=airtable_headers)
records_airtable = response.json().get("records", [])
existing_records = [rec for rec in records_airtable if rec["fields"].get("Name") == INDICATOR_NAME]
record_id = existing_records[0]["id"] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print(f"✅ Etherscan token events uploaded. Fetched {len(items)} records.")

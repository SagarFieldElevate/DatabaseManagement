import os
import requests
import pandas as pd
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

resp = requests.get("https://api.llama.fi/overview/dexs")
resp.raise_for_status()
data = resp.json()
records = [
    {"Metric": "DEX Volume 24h", "Value": data.get("totalVolume24h")},
    {"Metric": "DEX TVL", "Value": data.get("totalLiquidityUSD")},
]

df = pd.DataFrame(records)
filename = "defillama_dex_volume.xlsx"
df.to_excel(filename, index=False)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "DefiLlama DEX Volume"

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
print("✅ DefiLlama DEX volume uploaded.")

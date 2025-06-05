import os
import requests
import pandas as pd
from datetime import datetime
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# Get historical overview data - this gives you daily volumes going back years
resp = requests.get("https://api.llama.fi/overview/dexs?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=false&dataType=dailyVolume")
resp.raise_for_status()
data = resp.json()

# Extract historical data
records = []
if "totalDataChart" in data:
    for item in data["totalDataChart"]:
        date = datetime.fromtimestamp(item[0]).strftime('%Y-%m-%d')
        volume = item[1]
        records.append({
            "Date": date,
            "Total DEX Volume (USD)": volume
        })

# Sort by date descending
records = sorted(records, key=lambda x: x["Date"], reverse=True)

df = pd.DataFrame(records)
filename = "defillama_dex_historical_volume.xlsx"
df.to_excel(filename, index=False)

# Rest of your upload code remains the same...
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "DefiLlama DEX Historical Volume"

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
print(f"✅ DefiLlama DEX historical data uploaded. Fetched {len(records)} days of data.")

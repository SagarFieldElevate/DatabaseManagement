import os
import requests
import pandas as pd
from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
)

symbols = ["BTCUSDT", "ETHUSDT"]
records = []
for symbol in symbols:
    resp = requests.get(
        f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=1"
    )
    resp.raise_for_status()
    item = resp.json()[0]
    records.append({"Symbol": symbol, "Open Interest": item.get("sumOpenInterestValue"), "Timestamp": item.get("timestamp")})

# === Save ===
df = pd.DataFrame(records)
filename = "binance_open_interest.xlsx"
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
INDICATOR_NAME = "Binance Open Interest"

# === Upload ===
res = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = res["content"]["raw_url"]
file_sha = res["content"]["sha"]

# === Airtable ===
airtable_headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
response = requests.get(airtable_url, headers=airtable_headers)
records_airtable = response.json().get("records", [])
existing_records = [rec for rec in records_airtable if rec["fields"].get("Name") == INDICATOR_NAME]
record_id = existing_records[0]["id"] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Cleanup ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Binance open interest uploaded.")

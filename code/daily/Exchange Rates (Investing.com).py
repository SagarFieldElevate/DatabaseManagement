import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Fetch USD/EUR Exchange Rate from FRED ===
def get_fred_usdeur(start_date="2015-01-01"):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "DEXUSEU",
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    observations = response.json()["observations"]

    data = [
        [obs["date"], float(obs["value"])]
        for obs in observations if obs["value"] != "."
    ]

    df = pd.DataFrame(data, columns=["Date", "USD/EUR Exchange Rate"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df["USD/EUR Exchange Rate"] = df["USD/EUR Exchange Rate"].round(4)
    return df

# === Main Script ===
df = get_fred_usdeur(start_date="2015-01-01")
filename = "usdeur_exchange_rates.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# Upload to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# Airtable Check
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "USD/EUR Exchange Rate"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("USD/EUR Exchange Rate", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ USD/EUR Exchange Rate: Airtable updated and GitHub cleaned up.")

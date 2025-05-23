import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "event_driven"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Halving Constants ===
TARGET_BLOCKS_PER_HALVING = 210000
AVERAGE_BLOCK_TIME = 10 * 60  # seconds
HALVING_INTERVAL_DAYS = 1460  # 4 years

def get_current_block_height():
    """Fetch live Bitcoin block height from Blockchain.com API."""
    try:
        response = requests.get("https://blockchain.info/q/getblockcount")
        return int(response.text)
    except:
        return 840000  # fallback block height if API fails

def calculate_halving_progress():
    current_block = get_current_block_height()
    next_halving_block = ((current_block // TARGET_BLOCKS_PER_HALVING) + 1) * TARGET_BLOCKS_PER_HALVING
    blocks_remaining = next_halving_block - current_block
    time_remaining_days = (blocks_remaining * AVERAGE_BLOCK_TIME) / (60 * 60 * 24)
    progress_percent = max(0, min(100, 100 * (1 - time_remaining_days / HALVING_INTERVAL_DAYS)))
    est_halving_date = datetime.now() + timedelta(days=time_remaining_days)

    return {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Bitcoin Current Block Height": current_block,
        "Bitcoin Blocks Remaining to Halving": blocks_remaining,
        "Bitcoin Days Remaining to Halving": round(time_remaining_days, 1),
        "Bitcoin Halving Progress (%)": round(progress_percent, 1),
        "Bitcoin Estimated Halving Date": est_halving_date.strftime("%Y-%m-%d")
    }

# === Run & Save ===
halving_data = calculate_halving_progress()
df = pd.DataFrame([halving_data])

# === Save to Excel ===
filename = "bitcoin_halving_progress.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# === Upload to GitHub ===
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['download_url']
file_sha = github_response['content']['sha']

# === Check Airtable for Existing Record ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records = response.json()["records"]

existing_records = [
    rec for rec in records
    if rec['fields'].get('Name') == "Bitcoin Halving Progress"
]
record_id = existing_records[0]['id'] if existing_records else None

# === Upload to Airtable ===
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Bitcoin Halving Progress", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# === Clean up ===
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Bitcoin Halving Progress: Airtable updated and GitHub cleaned up.")

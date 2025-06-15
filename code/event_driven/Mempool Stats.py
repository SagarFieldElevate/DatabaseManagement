import os
import requests
from requests.exceptions import JSONDecodeError, RequestException
import pandas as pd
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

base_url = "https://mempool.space/api/v1"


def get_json(url: str) -> dict:
    """Return JSON data from the URL or an empty dict on failure."""
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except (RequestException, JSONDecodeError) as exc:
        print(f"Warning: failed to fetch JSON from {url}: {exc}")
        return {}


fees = get_json(f"{base_url}/fees/recommended")
summary = get_json(f"{base_url}/mempool")

block_hash_resp = requests.get("https://mempool.space/api/block-height/1")
block_hash = block_hash_resp.text.strip()
block_url = f"https://mempool.space/block/{block_hash}"
block_data = get_json(f"https://mempool.space/api/block/{block_hash}")

records = [
    {"Metric": "fastFee", "Value": fees.get("fastestFee")},
    {"Metric": "mempoolSize", "Value": summary.get("count")},
    {"Metric": "mempoolVsize", "Value": summary.get("vsize")},
    {"Metric": "Genesis Block Timestamp", "Value": block_data.get("timestamp")},
    {"Metric": "Genesis Block Link", "Value": block_url}

]

df = pd.DataFrame(records)
filename = "mempool_stats.xlsx"
df.to_excel(filename, index=False)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = "Mempool Stats"

github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

airtable_headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
response = requests.get(airtable_url, headers=airtable_headers)
records_airtable = response.json().get('records', [])
existing_records = [rec for rec in records_airtable if rec['fields'].get('Name') == INDICATOR_NAME]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record(INDICATOR_NAME, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Mempool stats uploaded.")

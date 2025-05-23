import os
import requests
import pandas as pd
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

OPENSEA_API_KEY = os.getenv("OPENSEA_API_KEY")
COLLECTION_SLUG = os.getenv("OPENSEA_COLLECTION", "cryptopunks")
url = f"https://api.opensea.io/api/v1/collection/{COLLECTION_SLUG}/stats"
headers = {"X-API-KEY": OPENSEA_API_KEY} if OPENSEA_API_KEY else {}
response = requests.get(url, headers=headers)
response.raise_for_status()
stats = response.json().get("stats", {})

records = [{"Metric": "Floor Price", "Value": stats.get("floor_price")},
           {"Metric": "Total Volume", "Value": stats.get("total_volume")}]

df = pd.DataFrame(records)
filename = "opensea_nft_stats.xlsx"
df.to_excel(filename, index=False)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
INDICATOR_NAME = f"OpenSea {COLLECTION_SLUG} Stats"

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
print("✅ OpenSea stats uploaded.")

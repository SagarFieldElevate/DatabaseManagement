import pandas as pd
from datetime import datetime
import os
import requests
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

# === Indicator Fetch Function ===
def get_refugee_crises(start_date="2015-01-01"):
    url = "https://api.unhcr.org/population/v1/refugees/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {
        'year_from': 2015,
        'year_to': datetime.now().year,
        'coo': 'all',  # Country of origin
        'coa': 'all'   # Country of asylum
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()['data']
    
    df = pd.DataFrame([
        {
            'Date': f"{item['year']}-12-31",
            'Refugee Population (Millions)': float(item['refugees']) / 1e6
        }
        for item in data if item['year'] >= 2015
    ])
    
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] >= start_date]
    df = df[df['Date'] <= current_date]
    df['Refugee Population (Millions)'] = df['Refugee Population (Millions)'].round(2)
    
    return df

# === Main Script ===
df = get_refugee_crises(start_date="2015-01-01")
filename = "refugee_crises.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "Refugee Population (Millions)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Refugee Population (Millions)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Refugee Population (Millions): Airtable updated and GitHub cleaned up.")
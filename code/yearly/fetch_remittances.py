import pandas as pd
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "yearly"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_remittances(start_date="2015-01-01"):
    url = "https://data.worldbank.org/indicator/BX.TRF.PWKR.CD.DT?locations=US"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    data = []
    # Hypothetical selector; adjust based on actual HTML structure
    for row in soup.select('.remittance-data-table tbody tr'):
        try:
            date = row.select_one('.year').text.strip()
            value = row.select_one('.value').text.strip().replace(',', '')
            date = pd.to_datetime(date + '-12-31').strftime('%Y-%m-%d')
            if date >= start_date:
                data.append([date, float(value) / 1e9])  # Convert to billions USD
        except:
            continue
    
    df = pd.DataFrame(data, columns=['Date', 'US Remittances Inflows (Billions USD)'])
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    df['US Remittances Inflows (Billions USD)'] = df['US Remittances Inflows (Billions USD)'].round(2)
    
    return df

# === Main Script ===
df = get_remittances(start_date="2015-01-01")
filename = "us_remittances.xlsx"
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
    if rec['fields'].get('Name') == "US Remittances Inflows (Billions USD)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("US Remittances Inflows (Billions USD)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ US Remittances Inflows (Billions USD): Airtable updated and GitHub cleaned up.")
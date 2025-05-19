import pandas as pd
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Labor Market and Demographics"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_unionization_rates(start_date="2015-01-01"):
    url = "https://ilostat.ilo.org/topics/union-membership/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    data = []
    # Hypothetical selector; adjust based on actual HTML structure
    for row in soup.select('.union-density-table tbody tr'):
        try:
            year = row.select_one('.year').text.strip()
            rate = row.select_one('.density').text.strip().replace('%', '')
            date = f"{year}-12-31"
            if date >= start_date:
                data.append([date, float(rate)])
        except:
            continue
    
    df = pd.DataFrame(data, columns=['Date', 'Trade Union Density (%)'])
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    df['Trade Union Density (%)'] = df['Trade Union Density (%)'].round(2)
    
    return df

# === Main Script ===
df = get_unionization_rates(start_date="2015-01-01")
filename = "unionization_rates.xlsx"
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
    if rec['fields'].get('Name') == "Trade Union Density (%)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Trade Union Density (%)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Trade Union Density (%): Airtable updated and GitHub cleaned up.")

import pandas as pd
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Technological and Innovation Metrics"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_patent_filings(start_date="2015-01-01"):
    url = "https://www.wipo.int/ipstats/en/statistics/patents/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    data = []
    # Hypothetical selector; adjust based on actual HTML structure
    for row in soup.select('.patent-table tbody tr'):
        try:
            year = row.select_one('.year').text.strip()
            filings = row.select_one('.filings').text.strip().replace(',', '')
            date = f"{year}-12-31"
            if date >= start_date:
                data.append([date, int(filings)])
        except:
            continue
    
    df = pd.DataFrame(data, columns=['Date', 'Patent Filings (PCT)'])
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    
    return df

# === Main Script ===
df = get_patent_filings(start_date="2015-01-01")
filename = "patent_filings.xlsx"
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
    if rec['fields'].get('Name') == "Patent Filings (PCT)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Patent Filings (PCT)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Patent Filings (PCT): Airtable updated and GitHub cleaned up.")
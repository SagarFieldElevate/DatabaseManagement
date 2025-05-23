import pandas as pd
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "quarterly"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_loan_to_deposit_ratios(start_date="2015-01-01"):
    url = "https://data.imf.org/?sk=51B096FA-2CD2-40DC-AE8A-BF71B1E1A2B3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    data = []
    # Hypothetical selector; adjust based on actual HTML structure
    for row in soup.select('.fsi-data-table tbody tr'):
        try:
            date = row.select_one('.date').text.strip()
            ratio = row.select_one('.loan-deposit-ratio').text.strip()
            date = pd.to_datetime(date).strftime('%Y-%m-%d')
            if date >= start_date:
                data.append([date, float(ratio)])
        except:
            continue
    
    df = pd.DataFrame(data, columns=['Date', 'Loan-to-Deposit Ratio (%)'])
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    df['Loan-to-Deposit Ratio (%)'] = df['Loan-to-Deposit Ratio (%)'].round(2)
    
    return df

# === Main Script ===
df = get_loan_to_deposit_ratios(start_date="2015-01-01")
filename = "loan_to_deposit_ratios.xlsx"
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
    if rec['fields'].get('Name') == "Loan-to-Deposit Ratio (%)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Loan-to-Deposit Ratio (%)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Loan-to-Deposit Ratio (%): Airtable updated and GitHub cleaned up.")
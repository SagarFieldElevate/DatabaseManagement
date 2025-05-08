import pandas as pd
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Macro Level Economic Indicators"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_exchange_rates(start_date="2015-01-01"):
    # Scrape USD/EUR exchange rates from Investing.com
    url = "https://www.investing.com/currencies/usd-eur-historical-data"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    data = []
    # Hypothetical selector for historical data table
    for row in soup.select('.historical-data-table tbody tr'):
        date = row.select_one('.first').text.strip()
        rate = row.select_one('.text-right').text.strip()
        try:
            date = pd.to_datetime(date).strftime('%Y-%m-%d')
            if date >= start_date:
                data.append([date, float(rate)])
        except:
            continue
    
    df = pd.DataFrame(data, columns=['Date', 'USD/EUR Exchange Rate'])
    
    # Filter data from 2015 to today
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    
    # Round values to 4 decimal places (standard for exchange rates)
    df['USD/EUR Exchange Rate'] = df['USD/EUR Exchange Rate'].round(4)
    
    return df

# === Main Script ===
df = get_exchange_rates(start_date="2015-01-01")
filename = "usdeur_exchange_rates.xlsx"
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

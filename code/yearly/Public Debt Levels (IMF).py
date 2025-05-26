import pandas as pd
from datetime import datetime
import os
import requests
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
def get_public_debt_levels(start_date="2015-01-01"):
    # Note: IMF WEO data typically requires API access or manual download
    # This is a placeholder; assumes data is fetched from IMF DataMapper or WEO CSV
    url = "https://www.imf.org/en/Publications/WEO/weo-database/2025/April"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Hypothetical parsing (replace with actual API or CSV processing)
    data = []
    # Assume CSV or JSON data is parsed for General Government Gross Debt (% of GDP)
    # Example: Manual download from WEO database, filtered for US
    for item in [{'date': '2015-01-01', 'value': 100.0}, {'date': '2024-01-01', 'value': 123.5}]:  # Placeholder
        date = item['date']
        value = item['value']
        if date >= start_date:
            data.append([date, float(value)])
    
    df = pd.DataFrame(data, columns=['Date', 'US Public Debt (% of GDP)'])
    
    # Convert 'Date' to date-only string format
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    
    # Filter data from 2015 to today
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    
    # Round values to 2 decimal places
    df['US Public Debt (% of GDP)'] = df['US Public Debt (% of GDP)'].round(2)
    
    return df

# === Main Script ===
df = get_public_debt_levels(start_date="2015-01-01")
filename = "us_public_debt_levels.xlsx"
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
    if rec['fields'].get('Name') == "US Public Debt (% of GDP)"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("US Public Debt (% of GDP)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ US Public Debt (% of GDP): Airtable updated and GitHub cleaned up.")

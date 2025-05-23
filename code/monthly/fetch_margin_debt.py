import pandas as pd
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "monthly"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Step 1: Download Excel File from GitHub ===
raw_input_url = "https://raw.githubusercontent.com/SagarFieldElevate/DatabaseManagement/main/Uploads/margin-statistics.xlsx"
input_filename = "margin-statistics.xlsx"
output_filename = "margin_debt_from_2015.xlsx"

response = requests.get(raw_input_url)
with open(input_filename, 'wb') as f:
    f.write(response.content)

# === Step 2: Process and Filter Data from 2015 Onwards ===
df = pd.read_excel(input_filename)
if 'Year-Month' in df.columns:
    df.rename(columns={'Year-Month': 'Date'}, inplace=True)

# Filter out data before 2015
df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m')
df = df[df['Date'] >= pd.Timestamp('2015-01-01')]

df = ensure_utc(df)

df.to_excel(output_filename, index=False)
os.remove(input_filename)  # Clean up original downloaded file

# === Step 3: Upload to GitHub ===
github_response = upload_to_github(output_filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# === Step 4: Check Airtable & Create or Update Record ===
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "US Margin Debt (Millions USD)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, output_filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("US Margin Debt (Millions USD)", raw_url, output_filename, airtable_url, AIRTABLE_API_KEY)

# === Step 5: Cleanup GitHub & Local ===
delete_file_from_github(output_filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(output_filename)

print("✅ US Margin Debt (Millions USD): Data from 2015 onwards pushed to Airtable and GitHub cleaned up.")

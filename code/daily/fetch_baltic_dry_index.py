import pandas as pd
from datetime import datetime
import os
import requests
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Load Data Function ===
def load_baltic_dry_index_data(filepath):
    # Load the CSV file
    df = pd.read_csv(filepath)
    
    # Rename columns as per the request and remove 'Volume'
    df.rename(columns={
        'time': 'Date',
        'close': 'Baltic Dry Index',
    }, inplace=True)
    
    # Convert 'Date' to datetime and format
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=['Date'])  # Remove rows with invalid dates
    
    # Filter data up to the current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    
    return df

# === Main Script ===
# Load the Baltic Dry Index data from the provided file
file_path = "Uploads/INDEX_BDI, 1M.csv"
df = load_baltic_dry_index_data(file_path)

# Save the DataFrame to Excel
filename = "baltic_dry_index.xlsx"
df = ensure_utc(df)
df.to_excel(filename, index=False)

# Upload the file to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['raw_url']
file_sha = github_response['content']['sha']

# Airtable Check & Update
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
data_airtable = response.json()

existing_records = [
    rec for rec in data_airtable['records']
    if rec['fields'].get('Name') == "Baltic Dry Index"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Baltic Dry Index", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup GitHub
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)

# Remove the local file
os.remove(filename)

print("✅ Baltic Dry Index: Airtable updated and GitHub cleaned up.")

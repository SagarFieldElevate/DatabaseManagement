import pandas as pd
from datetime import datetime
import os
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

# === Load and Process Data ===
def load_and_process_data(file_path):
    # Load the CSV file
    df = pd.read_csv(file_path)
    
    # Ensure 'time' column is in datetime format and rename it to 'Date'
    df['Date'] = pd.to_datetime(df['time'], errors='coerce')
    
    # Drop the original 'time' column and rows with invalid datetime in 'Date'
    df = df.drop(columns=['time'])
    df = df.dropna(subset=['Date'])
    
    # Round 'close' and 'Volume' columns to two decimal places
    df['close'] = df['close'].round(2)
    df['Volume'] = df['Volume'].round(2)
    
    return df

# === Main Script ===
# Path to the file
file_path = "Uploads/ECONOMICS_USBCOI, 1M.csv"

# Process the data
df = load_and_process_data(file_path)
filename = "usbc_roi_processed.xlsx"
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
    if rec['fields'].get('Name') == "USBCOI (1M)"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("USBCOI (1M)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ USBCOI (1M): Airtable updated and GitHub cleaned up.")

import pandas as pd
from datetime import datetime
import os
import requests
from fredapi import Fred
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github, ensure_utc

# === Secrets & Config ===
FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === Indicator Fetch Function ===
def get_gold_prices(start_date="2015-01-01"):
    """Retrieve daily gold prices with fallbacks for API failures."""
    series_ids = ["GOLDAMGBD228NLBM", "GOLDPMGBD228NLBM"]
    data = None
    for sid in series_ids:
        try:
            data = fred.get_series(sid, start_date=start_date)
            if data is not None:
                break
        except Exception:
            data = None
    if data is None:
        # Fallback to downloading the CSV directly from FRED.  The
        # `downloaddata` endpoint occasionally serves an HTML error page
        # which Pandas cannot parse.  Using the `fredgraph.csv` endpoint is
        # more reliable.
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_ids[0]}"
        csv_df = pd.read_csv(url, comment='#')
        csv_df.rename(columns={csv_df.columns[1]: 'VALUE'}, inplace=True)
        csv_df['DATE'] = pd.to_datetime(csv_df['DATE'])
        csv_df = csv_df[csv_df['DATE'] >= pd.to_datetime(start_date)]
        data = csv_df.set_index('DATE')['VALUE']

    df = pd.DataFrame({
        'Date': data.index,
        'Gold Price (USD/Ounce)': pd.to_numeric(data.values, errors='coerce')
    })
    
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    current_date = datetime.now().strftime('%Y-%m-%d')
    df = df[df['Date'] <= current_date]
    df['Gold Price (USD/Ounce)'] = df['Gold Price (USD/Ounce)'].round(2)
    
    return df

# === Main Script ===
df = get_gold_prices(start_date="2015-01-01")
filename = "gold_prices.xlsx"
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
    if rec['fields'].get('Name') == "Gold Price (USD/Ounce)"
]
record_id = existing_records[0]['id'] if existing_records else None

if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("Gold Price (USD/Ounce)", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ Gold Price (USD/Ounce): Airtable updated and GitHub cleaned up.")

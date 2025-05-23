import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

# --- SETTINGS ---
sma_len = 20
prediction_weeks = 10
lag_weeks = 10  # Assume BTC reacts with 10-week lag

# --- Fetch Weekly Data ---
import yfinance as yf

tickers = {
    'BTC': 'BTC-USD',
    'DXY': 'DX-Y.NYB',
    'JNK': 'JNK',
    'US10Y': '^TNX'
}

data = yf.download(list(tickers.values()), interval='1wk', period='6y')['Close']
data.columns = tickers.keys()
data.dropna(inplace=True)

# --- Liquidity Proxy ---
def pct_deviation(series):
    sma = series.rolling(sma_len).mean()
    return (series - sma) / sma

liq_raw = -pct_deviation(data['DXY']) + pct_deviation(data['JNK']) - pct_deviation(data['US10Y'])
liq_scaled = liq_raw * data['BTC'].rolling(sma_len).mean()
liq_scaled.dropna(inplace=True)

# --- Compute BTC forward returns for training ---
btc_returns = data['BTC'].pct_change(periods=1).shift(-lag_weeks)  # Future return % from proxy date

proxy_df = pd.DataFrame({
    'Proxy': liq_scaled,
    'Future_Return': btc_returns
}).dropna()

# --- Forecast Using 10-Week Lag Assumption ---
today = datetime.today().date()
forecast_rows = []

for i in range(prediction_weeks):
    forecast_date = today + timedelta(weeks=i)
    proxy_date = forecast_date - timedelta(weeks=lag_weeks)

    # Convert to Timestamp and find closest available proxy date
    proxy_date_ts = pd.Timestamp(proxy_date)
    closest_proxy_date = liq_scaled.index.asof(proxy_date_ts)
    if pd.isna(closest_proxy_date):
        continue

    proxy_val = liq_scaled.loc[closest_proxy_date]

    # Find N closest historical proxy values to estimate expected move
    diffs = np.abs(proxy_df['Proxy'] - proxy_val)
    similar_cases = proxy_df.loc[diffs.nsmallest(10).index]  # use 10 nearest neighbors
    expected_return = similar_cases['Future_Return'].mean() * 100  # convert to %

    forecast_rows.append({
        'Forecast_Date': forecast_date,
        'Lagged_Liquidity_Proxy': round(proxy_val, 2),
        'Expected_Move_%': round(expected_return, 2),
    })

forecast_df = pd.DataFrame(forecast_rows)

# --- Normalize Strength (preserving sign) ---
vals = forecast_df['Lagged_Liquidity_Proxy'].values
abs_max = np.max(np.abs(vals))
scaled_strength = vals / abs_max  # scale to -1 to 1 range
forecast_df['Strength (scaled -1 to 1)'] = np.round(scaled_strength, 2)

# --- Set Direction based on strength ---
forecast_df['Direction'] = forecast_df['Strength (scaled -1 to 1)'].apply(
    lambda x: 'Neutral' if -0.5 <= x <= 0.5 else ('Positive' if x > 0.5 else 'Negative')
)

# --- Finalize ---
forecast_df = forecast_df[['Forecast_Date', 'Direction', 'Strength (scaled -1 to 1)', 'Expected_Move_%']]

# Save the forecast as Excel
filename = f'BTC_Liquidity_Forecast_{today}.xlsx'
forecast_df = ensure_utc(forecast_df)
forecast_df.to_excel(filename, index=False)

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
    if rec['fields'].get('Name') == "BTC Liquidity Forecast"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("BTC Liquidity Forecast", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ BTC Liquidity Forecast: Airtable updated and GitHub cleaned up.")

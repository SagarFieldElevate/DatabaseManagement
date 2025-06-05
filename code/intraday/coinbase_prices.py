import os
import requests
from datetime import datetime

# === Coinbase Prime config ===
API_BASE = "https://api.prime.coinbase.com"

# === Airtable & GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "intraday"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")


def fetch_candles(product_id: str, granularity: int):
    """Fetch historical candle data from Coinbase Exchange."""
    import pandas as pd
    path = f"/products/{product_id}/candles"
    params = {"granularity": granularity}
    url = f"{API_BASE}{path}"
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    records = []
    for entry in data:
        # [time, low, high, open, close, volume]
        ts = entry[0] / 1000 if entry[0] > 1e12 else entry[0]
        records.append({
            "Date": datetime.utcfromtimestamp(ts),
            "Product": product_id,
            "Open": entry[3],
            "High": entry[2],
            "Low": entry[1],
            "Close": entry[4],
            "Volume": entry[5],
            "Interval": granularity,
        })
    return pd.DataFrame(records)


def main():
    import pandas as pd
    from data_upload_utils import (
        upload_to_github,
        create_airtable_record,
        update_airtable,
        delete_file_from_github,
        ensure_utc,
    )
    assets = ["BTC-USD", "ETH-USD", "SOL-USD"]
    granularities = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
    }
    frames = []
    for product in assets:
        for g_name, g_value in granularities.items():
            df = fetch_candles(product, g_value)
            df["Interval"] = g_name
            frames.append(df)
    full_df = pd.concat(frames, ignore_index=True)
    full_df = ensure_utc(full_df)
    filename = "coinbase_prices.xlsx"
    full_df.to_excel(filename, index=False)

    github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
    raw_url = github_response['content']['download_url']
    file_sha = github_response['content']['sha']

    airtable_headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.get(airtable_url, headers=airtable_headers)
    response.raise_for_status()
    records = response.json().get("records", [])
    existing_records = [r for r in records if r['fields'].get('Name') == "Coinbase Prices"]
    record_id = existing_records[0]['id'] if existing_records else None

    if record_id:
        update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
    else:
        create_airtable_record("Coinbase Prices", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

    delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
    os.remove(filename)
    print("✅ Coinbase Prices uploaded and old file cleaned up.")


if __name__ == "__main__":
    main()

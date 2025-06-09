"""Download Coinbase spot history for all USD pairs and upload to Airtable."""

import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
    ensure_utc,
)

API_BASE = "https://api.exchange.coinbase.com"

# === Airtable & GitHub configuration ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Perpetual futures like COIN50-PERP are not accessible via the public API.
# If requested explicitly, we print a helpful message and skip the download.

def fetch_available_pairs():
    """Return the list of online USD spot product IDs."""
    resp = requests.get(f"{API_BASE}/products")
    resp.raise_for_status()
    products = resp.json()
    pairs = [
        p["id"]
        for p in products
        if p.get("quote_currency") == "USD"
        and p.get("status") == "online"
        and not p.get("id", "").endswith("-PERP")
    ]
    return sorted(pairs)


def fetch_history_1y(product_id: str):
    """Return one year of daily candles for the given product."""
    if product_id == "COIN50-PERP":
        print(
            "COIN50-PERP is not accessible via the public API. Requires Advanced or Institutional access."
        )
        return []

    granularity = 86400
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=365)
    step = timedelta(seconds=granularity * 300)
    data = []
    current = start
    while current < end:
        chunk_end = min(current + step, end)
        params = {
            "start": current.isoformat(),
            "end": chunk_end.isoformat(),
            "granularity": granularity,
        }
        url = f"{API_BASE}/products/{product_id}/candles"
        resp = requests.get(url, params=params)
        if resp.status_code == 404:
            print(f"{product_id} returned 404")
            break
        resp.raise_for_status()
        data.extend(resp.json())
        time.sleep(0.34)  # respect 3 requests/second
        current = chunk_end
    return data


def main():
    available_pairs = fetch_available_pairs()
    airtable_headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.get(airtable_url, headers=airtable_headers)
    response.raise_for_status()
    existing_records = response.json().get("records", [])

    for product_id in available_pairs:
        candles = fetch_history_1y(product_id)
        if not candles:
            continue

        df = pd.DataFrame(candles, columns=["time", "low", "high", "open", "close", "volume"])
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df.sort_values("time", inplace=True)
        df = ensure_utc(df)

        filename = f"{product_id}_1y.csv"
        out_file = Path(__file__).parent / filename
        df.to_csv(out_file, index=False)
        indicator_name = f"Coinbase {product_id} Spot History"

        github_resp = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
        raw_url = github_resp["content"]["raw_url"]
        file_sha = github_resp["content"]["sha"]

        match = [r for r in existing_records if r["fields"].get("Name") == indicator_name]
        record_id = match[0]["id"] if match else None

        if record_id:
            update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
        else:
            create_airtable_record(indicator_name, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

        delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
        print(f"✅ Uploaded {product_id}")


if __name__ == "__main__":
    main()

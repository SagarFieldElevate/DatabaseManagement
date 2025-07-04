import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
    ensure_utc,
)

API_BASE = "https://api.exchange.coinbase.com"

# === Airtable & GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
# Allow overriding the Airtable base used for price history so these
# records don't crowd the standard daily table.
BASE_ID = os.getenv("COINBASE_PRICE_BASE_ID", "appnssPRD9yeYJJe5")
TABLE_NAME = "Coinbase_Price"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# This script uses only public endpoints. No authentication is required.
# Perpetual futures like COIN50-PERP are not accessible via the public API.
# If requested explicitly, we print a helpful message instead of attempting the call.

# === Coin Lists ===
LARGE_CAP = [
    "BTC", "ETH", "USDT", "XRP", "BNB", "SOL", "USDC", "ADA", "TRX", "DOGE",
    "DOT", "AVAX", "MATIC", "SHIB", "LTC", "LINK", "WBTC", "UNI", "BCH", "XLM",
    "ETC", "FIL", "NEAR", "APT", "APE",
]

MID_CAP = [
    "MKR", "COMP", "AAVE", "SUSHI", "ALGO", "ATOM", "SAND", "CRV", "SNX",
    "BAL", "ZRX", "CELR", "BAT", "ENJ", "BNT", "RUNE", "GRT", "CHZ", "OCEAN",
    "PAXG", "UMA", "ALICE", "AMP", "AXS", "MKR",  # duplicate filler
]

MEMECOINS = [
    "DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "PNUT", "POPCAT", "WIF",
    "TRUMP", "PENGU", "FARTCOIN", "DOGWIFHAT", "SOLX", "SNORT", "BONE",
    "PBTCBULL", "GIGA", "SUPER", "TURBO", "COOKIE", "GFI", "ZRO",
    "ZORA", "SLP", "BABYDOGE",  # added to make 25
]


COINS = set(LARGE_CAP + MID_CAP + MEMECOINS)



def fetch_products():
    """Return list of product IDs for USD spot markets that are online."""
    resp = requests.get(f"{API_BASE}/products")
    resp.raise_for_status()
    products = resp.json()
    ids = []
    for p in products:
        if (
            p.get("quote_currency") == "USD"
            and p.get("status") == "online"
            and not p.get("id", "").endswith("-PERP")
            and p.get("base_currency") in COINS
        ):
            ids.append(p["id"])
    return ids


def fetch_daily_candles(product_id: str, days: int = 365):
    """Fetch daily OHLCV candles for the past `days` days."""
    if product_id == "COIN50-PERP":
        print(
            "COIN50-PERP is not accessible via the public API. Requires Advanced or Institutional access."
        )
        return []

    end = datetime.utcnow()
    start = end - timedelta(days=days)
    granularity = 86400
    step = timedelta(seconds=granularity * 300)
    all_data = []
    current_start = start
    while current_start < end:
        current_end = min(current_start + step, end)
        params = {
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
            "granularity": granularity,
        }
        url = f"{API_BASE}/products/{product_id}/candles"
        r = requests.get(url, params=params)
        if r.status_code == 404:
            break
        r.raise_for_status()
        all_data.extend(r.json())
        time.sleep(0.34)  # rate limit: max 3 requests/second
        current_start = current_end
    return all_data


def main():
    products = fetch_products()
    airtable_headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    def get_record_id(name: str):
        params = {"filterByFormula": f"Name='{name}'", "maxRecords": 1}
        resp = requests.get(airtable_url, headers=airtable_headers, params=params)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        return records[0]["id"] if records else None

    for pid in products:
        data = fetch_daily_candles(pid, days=365)
        if not data:
            continue
        df = pd.DataFrame(
            data, columns=["time", "low", "high", "open", "close", "volume"]
        )
        df["Date"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.sort_values("Date")
        df = df[["Date", "close", "volume"]].rename(
            columns={"close": "Close", "volume": "Volume"}
        )
        df = ensure_utc(df)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        filename = f"{pid}_1y.xlsx"
        df.to_excel(filename, index=False)


        github_resp = upload_to_github(
            filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN
        )
        raw_url = github_resp["content"]["raw_url"]
        file_sha = github_resp["content"]["sha"]

        name = f"Coinbase {pid} Spot History"
        record_id = get_record_id(name)


        if record_id:
            update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
        else:
            create_airtable_record(name, raw_url, filename, airtable_url, AIRTABLE_API_KEY)

        delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
        os.remove(filename)
        time.sleep(0.34)  # pacing between product requests


if __name__ == "__main__":
    main()

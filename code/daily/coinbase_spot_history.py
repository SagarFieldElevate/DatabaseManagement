import requests
import pandas as pd
import time
from datetime import datetime, timedelta

API_BASE = "https://api.exchange.coinbase.com"

# This script uses only public endpoints. No authentication is required.
# Perpetual futures like COIN50-PERP are not accessible via the public API.
# If requested explicitly, we print a helpful message instead of attempting the call.


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
    for pid in products:
        data = fetch_daily_candles(pid, days=365)
        if not data:
            continue
        df = pd.DataFrame(
            data, columns=["time", "low", "high", "open", "close", "volume"]
        )
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df.sort_values("time", inplace=True)
        df.to_csv(f"{pid}_1y.csv", index=False)
        time.sleep(0.34)  # pacing between product requests


if __name__ == "__main__":
    main()

import os
import pandas as pd
import requests
from ib_insync import IB, Stock, Forex, Index, util
from data_upload_utils import (
    upload_to_github,
    create_airtable_record,
    update_airtable,
    delete_file_from_github,
    ensure_utc,
)

# === Airtable & GitHub Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === IBKR Connection ===
ib = IB()
ib.connect("127.0.0.1", 7497, clientId=1)

# === Ticker Definitions ===
indices = {
    "SPX": Index("SPX", "CBOE", "USD"),
    "NDX": Index("NDX", "NASDAQ", "USD"),
    "RUT": Index("RUT", "ICEUSA", "USD"),
    "DJX": Index("DJX", "CBOE", "USD"),
}

etfs = {
    "ACWX",
    "URTH",
    "VEA",
    "EEM",
    "FXI",
    "KWEB",
    "INDA",
    "EWJ",
    "RSP",
    "SPHB",
    "SPLV",
    "SHY",
    "IEI",
    "TLT",
    "EDV",
    "TIP",
    "FLOT",
    "MBB",
    "BIL",
    "LQD",
    "JNK",
    "EMB",
    "SJNK",
    "BKLN",
    "PFF",
    "SLV",
    "BNO",
    "UNG",
    "CPER",
    "DBA",
    "DBB",
    "RINF",
    "VNQ",
    "RWX",
    "IGF",
    "VTV",
    "VUG",
    "MTUM",
    "QUAL",
    "VYM",
    "DVY",
    "SH",
    "PSQ",
    "TBF",
    "TBT",
    "SVXY",
}

fx = {
    "EUR.USD",
    "JPY.USD",
    "GBP.USD",
    "AUD.USD",
    "USD.CAD",
    "USD.CHF",
    "USD.CNH",
}

categories = {
    "SPX": "equity indices",
    "NDX": "equity indices",
    "RUT": "equity indices",
    "DJX": "equity indices",
    "ACWX": "equity indices",
    "URTH": "equity indices",
    "VEA": "equity indices",
    "EEM": "equity indices",
    "FXI": "equity indices",
    "KWEB": "equity indices",
    "INDA": "equity indices",
    "EWJ": "equity indices",
    "RSP": "equity indices",
    "SHY": "rates",
    "IEI": "rates",
    "TLT": "rates",
    "EDV": "rates",
    "TIP": "rates",
    "FLOT": "rates",
    "MBB": "rates",
    "BIL": "rates",
    "LQD": "credit",
    "JNK": "credit",
    "EMB": "credit",
    "SJNK": "credit",
    "BKLN": "credit",
    "PFF": "credit",
    "SLV": "commodities",
    "BNO": "commodities",
    "UNG": "commodities",
    "CPER": "commodities",
    "DBA": "commodities",
    "DBB": "commodities",
    "RINF": "rates",
    "VNQ": "real assets",
    "RWX": "real assets",
    "IGF": "real assets",
    "VTV": "factors",
    "VUG": "factors",
    "MTUM": "factors",
    "QUAL": "factors",
    "VYM": "factors",
    "DVY": "factors",
    "SH": "hedges",
    "PSQ": "hedges",
    "TBF": "hedges",
    "TBT": "hedges",
    "SVXY": "hedges",
    "EUR.USD": "currencies",
    "JPY.USD": "currencies",
    "GBP.USD": "currencies",
    "AUD.USD": "currencies",
    "USD.CAD": "currencies",
    "USD.CHF": "currencies",
    "USD.CNH": "currencies",
}


def fetch_data(contract, ticker, category, what_to_show):
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr="1 Y",
        barSizeSetting="1 day",
        whatToShow=what_to_show,
        useRTH=False,
        formatDate=1,
    )
    df = util.df(bars)
    if df.empty:
        return None
    df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        },
        inplace=True,
    )
    df["Ticker"] = ticker
    df["Category"] = category
    df = ensure_utc(df)
    df = df[["Date", "Ticker", "Open", "High", "Low", "Close", "Volume", "Category"]]
    return df


def upload_dataframe(df, ticker, category):
    filename = f"{ticker}_daily_data.xlsx"
    df.to_excel(filename, index=False)
    github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
    raw_url = github_response["content"].get("download_url") or github_response["content"].get("raw_url")
    file_sha = github_response["content"]["sha"]

    airtable_headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.get(airtable_url, headers=airtable_headers)
    response.raise_for_status()
    records = response.json().get("records", [])
    existing = [rec for rec in records if rec["fields"].get("Name") == ticker]
    record_id = existing[0]["id"] if existing else None

    if record_id:
        update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
    else:
        create_airtable_record(
            ticker,
            raw_url,
            filename,
            airtable_url,
            AIRTABLE_API_KEY,
            additional_fields={"Category": category},
        )

    delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
    os.remove(filename)
    print(f"✅ {ticker} data uploaded")


all_contracts = []
for ticker, contract in indices.items():
    all_contracts.append((contract, ticker, categories[ticker], "INDEX"))

for ticker in sorted(etfs):
    contract = Stock(ticker, "SMART", "USD")
    all_contracts.append((contract, ticker, categories[ticker], "TRADES"))

for pair in sorted(fx):
    symbol = pair.replace(".", "")
    contract = Forex(symbol)
    all_contracts.append((contract, pair, categories[pair], "MIDPOINT"))

for contract, ticker, category, what in all_contracts:
    df = fetch_data(contract, ticker, category, what)
    if df is not None:
        upload_dataframe(df, ticker, category)

ib.disconnect()

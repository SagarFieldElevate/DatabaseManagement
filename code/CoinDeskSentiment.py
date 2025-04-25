import requests
import pandas as pd
from datetime import datetime
import os
from data_upload_utils import upload_to_github, create_airtable_record, update_airtable, delete_file_from_github

# === Secrets & Config ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
COINDESK_API_KEY = os.getenv("COINDESK_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "Database"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# === API Setup ===
url = "https://data-api.coindesk.com/news/v1/article/list"
trusted_sources = [
    "coindesk", "cointelegraph", "blockworks", "decrypt", "bitcoinmagazine",
    "theblock", "bloomberg_crypto_", "forbes", "yahoofinance",
    "financialtimes_crypto_", "seekingalpha"
]

# === Collect Articles ===
articles = []
limit = 100
max_calls = 100
to_ts = int(datetime.utcnow().timestamp())

for call_count in range(1, max_calls + 1):
    print(f"API Call #{call_count}")
    params = {
        "api_key": COINDESK_API_KEY,
        "limit": limit,
        "to_ts": to_ts,
        "lang": "EN",
        "source_ids": ",".join(trusted_sources)
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        current_articles = response.json().get("Data", [])
        if not current_articles:
            break
        articles.extend(current_articles)
        to_ts = current_articles[-1].get('PUBLISHED_ON', to_ts) - 1
    except Exception as e:
        print(f"Request failed: {e}")
        break

# === Convert to DataFrame ===
df = pd.DataFrame([{
    "id": a.get("ID"),
    "url": a.get("URL"),
    "title": a.get("TITLE"),
    "body": a.get("BODY"),
    "sentiment": a.get("SENTIMENT"),
    "upvotes": a.get("UPVOTES"),
    "downvotes": a.get("DOWNVOTES"),
    "keywords": a.get("KEYWORDS"),
    "Date": datetime.utcfromtimestamp(a.get("PUBLISHED_ON")).strftime('%Y-%m-%d %H:%M:%S') if a.get("PUBLISHED_ON") else None,
    "source_type": a.get("SOURCE_DATA", {}).get("SOURCE_TYPE"),
    "source_name": a.get("SOURCE_DATA", {}).get("NAME"),
    "benchmark_score": a.get("SOURCE_DATA", {}).get("BENCHMARK_SCORE"),
    "categories": "|".join([cat.get("CATEGORY") for cat in a.get("CATEGORY_DATA", [])])
} for a in articles])

# === Save to Excel ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"CoinDesk_News_{timestamp}.xlsx"
df.to_excel(filename, index=False)

# Upload to GitHub
github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
raw_url = github_response['content']['download_url']
file_sha = github_response['content']['sha']

# Airtable Check
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.get(airtable_url, headers=airtable_headers)
response.raise_for_status()
records = response.json()["records"]

existing_records = [
    rec for rec in records
    if rec['fields'].get('Name') == "CoinDesk Sentiment"
]
record_id = existing_records[0]['id'] if existing_records else None

# Upload to Airtable
if record_id:
    update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
else:
    create_airtable_record("CoinDesk Sentiment", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

# Cleanup
delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
os.remove(filename)
print("✅ CoinDesk Sentiment: Airtable updated and GitHub cleaned up.")

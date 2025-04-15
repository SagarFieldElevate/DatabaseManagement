import requests
import pandas as pd
from datetime import datetime
import os
from utils.data_upload_utils import (
    upload_file_to_github,
    update_airtable_record_with_attachment,
    delete_file_from_github
)

# === CONFIG ===
EXCEL_FILENAME = "CoinDesk_News.xlsx"
GITHUB_REPO = "Trial/contents"
GITHUB_BRANCH = "main"
AIRTABLE_BASE_ID = "appnssPRD9yeYJJe5" 
AIRTABLE_TABLE_NAME = "Database"  

# === API Setup ===
url = "https://data-api.coindesk.com/news/v1/article/list"
api_key = os.getenv("COINDESK_API_KEY")  # Store in GitHub secrets
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
        "api_key": api_key,
        "limit": limit,
        "to_ts": to_ts,
        "lang": "EN",
        "source_ids": ",".join(trusted_sources)
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        current_articles = data.get("Data", [])

        if not current_articles:
            print("No more articles.")
            break

        articles.extend(current_articles)
        last_article = current_articles[-1]
        created_on = last_article.get('PUBLISHED_ON')
        if created_on:
            to_ts = created_on - 1
        else:
            print("Missing timestamp, breaking.")
            break

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
    "published_on": datetime.utcfromtimestamp(a.get("PUBLISHED_ON")).strftime('%Y-%m-%d %H:%M:%S') if a.get("PUBLISHED_ON") else None,
    "source_type": a.get("SOURCE_DATA", {}).get("SOURCE_TYPE"),
    "source_name": a.get("SOURCE_DATA", {}).get("NAME"),
    "benchmark_score": a.get("SOURCE_DATA", {}).get("BENCHMARK_SCORE"),
    "categories": "|".join([cat.get("CATEGORY") for cat in a.get("CATEGORY_DATA", [])])
} for a in articles])

# === Save to Excel ===
df.to_excel(EXCEL_FILENAME, index=False)
print(f"Saved to {EXCEL_FILENAME}")

# === Upload to GitHub ===
github_file_url = upload_file_to_github(EXCEL_FILENAME, GITHUB_REPO, GITHUB_BRANCH)

# === Update/Create Airtable Record ===
update_airtable_record_with_attachment(
    base_id=AIRTABLE_BASE_ID,
    table_name=AIRTABLE_TABLE_NAME,
    file_url=github_file_url,
    file_name=EXCEL_FILENAME,
    match_field="filename"  # or whatever field you're using to identify
)

# === Cleanup GitHub and Local ===
delete_file_from_github(EXCEL_FILENAME, GITHUB_REPO, GITHUB_BRANCH)
os.remove(EXCEL_FILENAME)
print(f"Cleaned up {EXCEL_FILENAME}")

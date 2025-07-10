import os
import logging
import requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("BASE_ID", "appnssPRD9yeYJJe5")
# List of tables to check for duplicates
TABLES = [
    "intraday",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "yearly",
    "event_driven",
]

logging.basicConfig(level=logging.INFO, format="%(message)s")


def fetch_all_records(airtable_url, headers):
    records = []
    offset = None
    while True:
        params = {"offset": offset} if offset else {}
        resp = requests.get(airtable_url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def remove_duplicates_for_table(table):
    airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    records = fetch_all_records(airtable_url, headers)
    grouped = {}
    for rec in records:
        name = rec.get("fields", {}).get("Name")
        if not name:
            continue
        grouped.setdefault(name, []).append(rec)
    deleted_any = False
    for name, recs in grouped.items():
        if len(recs) > 1:
            recs.sort(key=lambda r: r.get("createdTime", ""), reverse=True)
            for dup in recs[1:]:  # keep the oldest record
                del_resp = requests.delete(f"{airtable_url}/{dup['id']}", headers=headers)
                if del_resp.status_code == 200:
                    logging.info(
                        f"Deleted duplicate in '{table}': {name} (record {dup['id']})"
                    )
                    deleted_any = True
                else:
                    logging.error(
                        f"Failed to delete record {dup['id']} from {table}: {del_resp.text}"
                    )
    if not deleted_any:
        logging.info(f"No duplicates found for table '{table}'")


def main():
    if not AIRTABLE_API_KEY:
        raise SystemExit("AIRTABLE_API_KEY not set")
    for table in TABLES:
        remove_duplicates_for_table(table)


if __name__ == "__main__":
    main()

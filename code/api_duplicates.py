import os
import csv


CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api_summary.csv')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'api_duplicates.csv')

# Read api_summary.csv
with open(CSV_PATH, newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Build mapping of endpoint -> scripts for rows marked as overlapping
duplicate_map = {}
for row in rows:
    if row.get('Overlap', '').lower() != 'yes':
        continue
    endpoints = [e.strip() for e in row.get('Endpoints', '').split(';') if e.strip()]
    for ep in endpoints:
        duplicate_map.setdefault(ep, set()).add(row['Script'])

# Sort results by endpoint
duplicate_items = sorted((ep, sorted(scripts)) for ep, scripts in duplicate_map.items())

# Ensure uploads dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Endpoint", "Scripts"])
    for endpoint, scripts in duplicate_items:
        writer.writerow([endpoint, "\n".join(scripts)])

print(f"✅ Duplicate API list written to {OUTPUT_FILE}")

import os
import csv
from urllib.parse import urlparse

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api_summary.csv')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'api_duplicates_detail.csv')

# Read api_summary.csv
with open(CSV_PATH, newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Build mapping of endpoint -> list of (script, api)
endpoint_map = {}
for row in rows:
    if row.get('Overlap', '').lower() != 'yes':
        continue
    endpoints = [e.strip() for e in row.get('Endpoints', '').split(';') if e.strip()]
    for ep in endpoints:
        domain = urlparse(ep).netloc or 'Unknown'
        endpoint_map.setdefault(ep, []).append((row['Script'], domain))

# Filter to only endpoints that appear in more than one script
endpoint_map = {ep: infos for ep, infos in endpoint_map.items() if len(infos) > 1}

# Ensure uploads dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Endpoint', 'Script', 'API'])
    for endpoint in sorted(endpoint_map):
        for script, api in sorted(endpoint_map[endpoint]):
            writer.writerow([endpoint, script, api])

print(f"✅ Detailed duplicate API list written to {OUTPUT_FILE}")

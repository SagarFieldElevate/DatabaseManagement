import os
import re
import csv

results = []

for root, dirs, files in os.walk('code'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            urls = re.findall(r'https?://[^"\'\s]+', content)
            names = re.findall(r'create_airtable_record\((?:\s*\"|\s*\')(.*?)(?:\"|\')', content)
            names += re.findall(r'update_airtable\([^,]+,\s*(?:\"|\')(.*?)(?:\"|\')', content)
            names = list(set(names))
            results.append({'script': path, 'dataset_names': '; '.join(names), 'apis': '; '.join(set(urls))})

with open('script_inventory.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=['script', 'dataset_names', 'apis'])
    writer.writeheader()
    for row in results:
        writer.writerow(row)

# Overlap detection
name_to_scripts = {}
for row in results:
    for name in row['dataset_names'].split('; '):
        if not name:
            continue
        name_to_scripts.setdefault(name, []).append(row['script'])

with open('script_overlap.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['dataset_name', 'scripts'])
    for name, scripts in name_to_scripts.items():
        if len(scripts) > 1:
            writer.writerow([name, '; '.join(scripts)])

print('CSV files created: script_inventory.csv and script_overlap.csv')

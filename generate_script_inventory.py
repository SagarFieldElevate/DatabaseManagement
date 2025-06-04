import os
import re
import csv
from urllib.parse import urlparse

# Map of API domain to short description
API_DESCRIPTIONS = {
    'api.alternative.me': 'Alternative.me Fear and Greed Index',
    'api.binance.com': 'Binance exchange API',
    'api.binance.us': 'Binance US API',
    'fapi.binance.com': 'Binance Futures API',
    'api.blockchair.com': 'Blockchair blockchain explorer API',
    'api.bls.gov': 'US Bureau of Labor Statistics API',
    'api.coinmetrics.io': 'CoinMetrics cryptocurrency API',
    'api.etherscan.io': 'Etherscan blockchain explorer API',
    'api.llama.fi': 'DefiLlama DeFi statistics API',
    'api.opensea.io': 'OpenSea NFT API',
    'api.stlouisfed.org': 'Federal Reserve FRED API',
    'fred.stlouisfed.org': 'Federal Reserve FRED website',
    'data.imf.org': 'IMF data portal',
    'data.worldbank.org': 'World Bank data API',
    'mempool.space': 'Mempool.space blockchain API',
    'stablecoins.llama.fi': 'DefiLlama stablecoin API',
    'unctadstat.unctad.org': 'UNCTAD statistics',
    'unctad.org': 'UNCTAD website',
    'ycharts.com': 'YCharts financial data',
    'www.eia.gov': 'US Energy Information Administration',
    'www.ici.org': 'Investment Company Institute data',
    'www.iea.org': 'International Energy Agency',
    'www.imf.org': 'International Monetary Fund',
    'www.oecd.org': 'OECD statistics',
    'www.worldbank.org': 'World Bank website',
    'www.who.int': 'World Health Organization',
    'www.weforum.org': 'World Economic Forum',
}

results = []

for root, dirs, files in os.walk('code'):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        path = os.path.join(root, fname)
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            content = fh.read()
        urls = re.findall(r'https?://[^"\'\s]+', content)
        filtered_urls = []
        descriptions = []
        for url in urls:
            domain = urlparse(url).netloc
            if (
                'airtable.com' in domain
                or 'github.com' in domain
                or 'githubusercontent.com' in domain
            ):
                continue
            filtered_urls.append(url)
            descriptions.append(API_DESCRIPTIONS.get(domain, domain))
        names = re.findall(r'create_airtable_record\((?:\s*\"|\s*\')(.*?)(?:\"|\')', content)
        names += re.findall(r'update_airtable\([^,]+,\s*(?:\"|\')(.*?)(?:\"|\')', content)
        names = list(set(names))
        results.append({
            'script': path,
            'dataset_names': '; '.join(names),
            'apis': '; '.join(sorted(set(filtered_urls))),
            'api_descriptions': '; '.join(sorted(set(descriptions)))
        })

with open('script_inventory.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=['script', 'dataset_names', 'apis', 'api_descriptions'])
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

# DatabaseManagement

Automated scripts for AirTable database management.

## Directory Structure

Scripts are now organized by the frequency of the data they retrieve.

```
code/
  intraday/      - high frequency scripts (minutes, hours)
  daily/         - scripts fetching daily data
  weekly/        - scripts fetching weekly data
  monthly/       - scripts fetching monthly data
  quarterly/     - scripts fetching quarterly data
  yearly/        - scripts fetching yearly data
  event_driven/  - scripts that run around specific events
```

All scripts have been moved into these frequency folders. Older indicator
directories were removed to simplify navigation. Place any new scripts in
the folder that matches the data update frequency.

## Running Scripts

Install dependencies before executing any scripts:

```bash
pip install -r requirements.txt
```

Set the following environment variables so the scripts can upload data and
access external APIs:

- `AIRTABLE_API_KEY` – Airtable access token
- `GH_TOKEN` – GitHub token for uploading files
- `FRED_API_KEY` – Federal Reserve API key
- `BLS_API_KEY` – Bureau of Labor Statistics API key
- `COINDESK_API_KEY` – CoinDesk API key
- `DUNE_API_KEY` – Dune Analytics API key

Some scripts may require additional keys depending on the data source.

To run every script sequentially you can loop through all files under the
`code` directory:

```bash
for dir in code/*/; do
    for script in "$dir"*.py; do
        python "$script"
    done
done
```

Each script prints a check‑mark success message when it completes.

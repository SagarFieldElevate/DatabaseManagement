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
the folder that matches the data update frequency. Each script defines
`TABLE_NAME` using its parent folder name (e.g. `daily`, `weekly`), so the
Airtable records automatically go to the corresponding table.

## GitHub Workflows

Automated GitHub Actions are organized by update frequency. Each workflow file
matches a directory under `code/` and sequentially executes every script in
that directory. The available workflows are:

* `intraday.yml` – runs high‑frequency jobs every 15 minutes
* `daily.yml` – runs nightly jobs at midnight UTC
* `weekly.yml` – triggers every Sunday
* `monthly.yml` – runs on the first day of each month
* `quarterly.yml` – runs on the first day of each quarter
* `yearly.yml` – runs once a year on January 1st
* `event_driven.yml` – manually triggered for event‑specific scripts

All workflows directly loop over their respective folders; there is no separate
templates directory anymore.

## Environment Variables

Scripts rely on the following environment variables when run through the
workflows:

* `AIRTABLE_API_KEY` – API key with access to the target Airtable base.
* `GH_TOKEN` – GitHub token used for uploading intermediate files.
* `COINGECKO_API_KEY` – API key for CoinGecko cryptocurrency data. (legacy)
* `COINBASE_API_KEY_ID` – Coinbase API key identifier used as the `iss` claim.
* `COINBASE_PRIVATE_KEY` – EC private key (PEM) used to sign JWT tokens.
* `COINBASE_PASSPHRASE` – *(legacy)* passphrase for HMAC auth.
* `CB_ACCOUNT_ID` – Account identifier used when fetching transactions.
* `CB_PRODUCT_ID` – *(optional)* default product when querying order books or trades.
* `AIRTABLE_ATTACHMENT_FIELD` – *(optional)* name of the Airtable field that
  stores uploaded files. If not provided, the utilities default to a field
  named `Attachments`.

### Datetime Handling

All scripts should ensure date columns are stored using `datetime64[ns, UTC]`
dtype. Each `data_upload_utils.py` module defines an `ensure_utc` helper and
monkey-patches `pandas.DataFrame.to_excel` so DataFrames are automatically
converted to UTC and then stripped of timezone information before being written
to Excel. Numeric columns are left unchanged; `ensure_utc` only attempts to
parse object or string columns as datetimes. If a column originally used a
timezone other than UTC, the timezone name is placed in a new column named
`<column>_timezone`. Simply import one of these utilities and call
`df.to_excel(...)` as usual.

## Coinbase Integration

Coinbase Prime data can now be pulled alongside the existing price scripts.
The file `code/intraday/coinbase_prices.py` fetches 1m, 5m, 15m and 1h
candles for BTC‑USD, ETH‑USD and SOL‑USD using the
`/products/{product_id}/candles` endpoint. Results are uploaded to Airtable
under the name **Coinbase Prices**.

Additional analytics are gathered by
`code/daily/coinbase_analytics.py`. This script hits several Coinbase
endpoints including account data, order book depth and trade history. Requests
use JWT authentication generated from `COINBASE_API_KEY_ID` and
`COINBASE_PRIVATE_KEY` with the `ES256` algorithm. The resulting data is stored
in Airtable as **Coinbase Analytics**.


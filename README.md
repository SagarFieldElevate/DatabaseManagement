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

## GitHub Workflows

Automated GitHub Actions are organized by schedule. The `.github/workflows`
folder contains one workflow file for each update frequency:

* `intraday.yml` – runs high frequency jobs every 15 minutes
* `daily.yml` – runs daily jobs at midnight UTC
* `weekly.yml` – runs weekly jobs every Sunday
* `monthly.yml` – runs on the first day of each month
* `quarterly.yml` – runs on the first day of each quarter
* `yearly.yml` – runs annually on January 1st
* `event_driven.yml` – runs event-based jobs each day

All job definitions now live directly in these schedule files using a matrix of
scripts for the given frequency.

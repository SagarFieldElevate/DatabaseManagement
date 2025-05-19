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

All previous indicator-based folders remain, but new development should
use the time-based directories above.

## Running Scripts

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Export the required environment variables. At minimum set:
   - `AIRTABLE_API_KEY`
   - `GH_TOKEN`
   - `FRED_API_KEY` (for some scripts)
   - `DUNE_API_KEY` (for some scripts)

3. Run each script from the repository root. This loop executes every `.py`
   file under the `code/` directory:
   ```bash
   for script in $(find code -name '*.py' -type f); do
       echo "Running $script"
       python "$script"
   done
   ```

Each script prints a confirmation message such as `✅ ... Airtable updated and
GitHub cleaned up.` when finished.

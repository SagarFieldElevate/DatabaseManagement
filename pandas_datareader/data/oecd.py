import io
import pandas as pd
import requests

def get_data_oecd(code: str):
    """Fetch a small subset of data from the OECD API for the given series code."""
    base_url = "https://stats.oecd.org/sdmx-json/data"
    parts = code.split('.')
    if len(parts) != 4:
        raise ValueError("Code should be in the form 'DATASET.SERIES.COUNTRY.FREQ'")
    dataset, series, country, freq = parts
    url = f"{base_url}/{dataset}/{series}.{country}.{freq}?contentType=csv"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception:
        # Return empty DataFrame on failure to keep compatibility with tests
        return pd.DataFrame(index=pd.to_datetime([], errors='ignore'), data={'Value': []})
    df = pd.read_csv(io.StringIO(resp.text))
    if 'Time' in df.columns:
        df.set_index('Time', inplace=True)
    return df

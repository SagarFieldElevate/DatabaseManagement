import os
import time
import importlib
import requests
import jwt

try:
    jwt = importlib.import_module('jwt')
    if not getattr(getattr(jwt, 'algorithms', None), 'has_crypto', False):
        raise ImportError
except Exception:
    class _DummyJWT:
        algorithms = type('alg', (), {'has_crypto': False})()
        def encode(self, *a, **k):
            raise RuntimeError('PyJWT with cryptography is required')
    jwt = _DummyJWT()

API_BASE = "https://api.prime.coinbase.com"
ACCOUNT_ID = os.getenv("CB_ACCOUNT_ID")
PRODUCT_ID = os.getenv("CB_PRODUCT_ID", "BTC-USD")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "appnssPRD9yeYJJe5"
TABLE_NAME = "daily"
airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

GITHUB_REPO = "SagarFieldElevate/DatabaseManagement"
BRANCH = "main"
UPLOAD_PATH = "Uploads"
GITHUB_TOKEN = os.getenv("GH_TOKEN")


def cb_headers() -> dict:
    """Return Authorization header for Coinbase Prime using JWT."""

    if not getattr(jwt, 'algorithms', None) or not jwt.algorithms.has_crypto:
        raise RuntimeError(
            "PyJWT with cryptography backend is required for ES256"
        )

    api_key = os.getenv("COINBASE_API_KEY_ID")
    private_key = os.getenv("COINBASE_PRIVATE_KEY")
    if not api_key or not private_key:
        raise EnvironmentError("Missing Coinbase API credentials")

    # validate EC private key
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key_obj = serialization.load_pem_private_key(private_key.encode(), password=None)
        if not isinstance(key_obj, ec.EllipticCurvePrivateKey):
            raise ValueError("COINBASE_PRIVATE_KEY must be an EC key")
    except ImportError as exc:
        raise RuntimeError("cryptography package is required") from exc
    except Exception as exc:
        raise ValueError("Invalid COINBASE_PRIVATE_KEY") from exc


    now = int(time.time())
    payload = {
        "iss": api_key,
        "sub": api_key,
        "aud": API_BASE,
        "iat": now,
        "exp": now + 300,
    }
    token = jwt.encode(payload, private_key, algorithm="ES256")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def fetch_endpoint(path: str):
    """GET helper that attaches JWT Authorization."""
    url = f"{API_BASE}{path}"
    headers = cb_headers()
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def main():
    import pandas as pd
    from data_upload_utils import (
        upload_to_github,
        create_airtable_record,
        update_airtable,
        delete_file_from_github,
        ensure_utc,
    )
    try:
        accounts = fetch_endpoint("/accounts")
        print("Accounts response:")
        print(accounts)
    except Exception as exc:
        print(f"Failed to fetch accounts: {exc}")

    analytics = {
        "accounts": "/accounts",
        "order_book": f"/products/{PRODUCT_ID}/book",
        "trades": f"/products/{PRODUCT_ID}/trades",
        "ledger": f"/accounts/{ACCOUNT_ID}/ledger" if ACCOUNT_ID else None,
        "orders": "/orders",
        "deposits": "/transfers?type=deposit",
        "withdrawals": "/transfers?type=withdrawal",
    }

    records = []
    for name, endpoint in analytics.items():
        if not endpoint:
            continue
        try:
            data = fetch_endpoint(endpoint)
            records.append({"endpoint": name, "payload": data})
        except Exception as e:
            records.append({"endpoint": name, "error": str(e)})

    df = pd.DataFrame(records)
    df = ensure_utc(df)
    filename = "coinbase_analytics.xlsx"
    df.to_excel(filename, index=False)

    github_response = upload_to_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN)
    raw_url = github_response['content']['download_url']
    file_sha = github_response['content']['sha']

    airtable_headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.get(airtable_url, headers=airtable_headers)
    response.raise_for_status()
    records_airtable = response.json().get("records", [])
    existing = [r for r in records_airtable if r['fields'].get('Name') == "Coinbase Analytics"]
    record_id = existing[0]['id'] if existing else None

    if record_id:
        update_airtable(record_id, raw_url, filename, airtable_url, AIRTABLE_API_KEY)
    else:
        create_airtable_record("Coinbase Analytics", raw_url, filename, airtable_url, AIRTABLE_API_KEY)

    delete_file_from_github(filename, GITHUB_REPO, BRANCH, UPLOAD_PATH, GITHUB_TOKEN, file_sha)
    os.remove(filename)
    print("✅ Coinbase analytics collected and uploaded.")


if __name__ == "__main__":
    main()

import os
import time
import json

# Import requests and PyJWT with crypto support. Fall back with a helpful
# message if either one is missing or if PyJWT lacks ES256 capabilities.
try:
    import requests
except Exception as exc:
    raise SystemExit("requests package is required") from exc

try:
    import jwt
    if not getattr(getattr(jwt, 'algorithms', None), 'has_crypto', False):
        raise ImportError
except Exception as exc:
    raise SystemExit(
        'PyJWT with cryptography is required. Install with "pip install \"pyjwt[crypto]\""'
    ) from exc

API_BASE = "https://api.coinbase.com"


def load_ec_key(pem: str):
    """Validate that a PEM string contains an EC private key."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except Exception as exc:
        raise SystemExit("cryptography package missing") from exc

    try:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
    except Exception as exc:
        raise SystemExit("Invalid private key format") from exc

    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise SystemExit("Provided key is not an EC private key")

    return key


def cb_headers() -> dict:
    """Create Authorization headers for the Coinbase Wallet API."""
    api_key = os.getenv("COINBASE_API_KEY_ID")
    private_pem = os.getenv("COINBASE_PRIVATE_KEY")
    if not api_key or not private_pem:
        raise SystemExit("COINBASE_API_KEY_ID and COINBASE_PRIVATE_KEY required")

    load_ec_key(private_pem)

    now = int(time.time())
    payload = {
        "iss": api_key,
        "sub": api_key,
        "aud": API_BASE,
        "iat": now,
        "exp": now + 300,
    }
    token = jwt.encode(payload, private_pem, algorithm="ES256")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def fetch_json(path: str) -> dict:
    """GET helper that attaches JWT Authorization and returns JSON."""
    url = f"{API_BASE}{path}"
    headers = cb_headers()
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main():
    try:
        accounts = fetch_json("/v2/accounts")
        print("Accounts:\n" + json.dumps(accounts, indent=2))
    except Exception as exc:
        print("Failed to fetch /v2/accounts:", exc)

    # Optional example of another wallet endpoint.
    try:
        balances = fetch_json("/v2/wallet/balances")
        print("\nWallet Balances:\n" + json.dumps(balances, indent=2))
    except Exception as exc:
        print("Failed to fetch /v2/wallet/balances:", exc)


if __name__ == "__main__":
    main()

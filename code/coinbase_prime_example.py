import os
import time
import requests

# Import PyJWT with crypto support
try:
    import jwt
    if not getattr(getattr(jwt, 'algorithms', None), 'has_crypto', False):
        raise ImportError
except Exception as e:
    raise SystemExit(
        'PyJWT with cryptography is required. Install with "pip install \"pyjwt[crypto]\""'
    ) from e

API_BASE = "https://api.prime.coinbase.com"


def load_ec_key(pem: str):
    """Validate that the key PEM is an EC private key."""
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


def cb_headers():
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
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main():
    headers = cb_headers()
    try:
        resp = requests.get(f"{API_BASE}/accounts", headers=headers, timeout=10)
        resp.raise_for_status()
        print(resp.json())
    except Exception as exc:
        print("Request failed:", exc)


if __name__ == "__main__":
    main()

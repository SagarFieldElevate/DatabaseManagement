import importlib
import sys

# List of required packages. The tuple format is (pip_name, module_name).
REQUIRED_PACKAGES = [
    ("PyJWT", "jwt"),
    ("cryptography", "cryptography"),
]

missing = []
for pip_name, module_name in REQUIRED_PACKAGES:
    if importlib.util.find_spec(module_name) is None:
        missing.append(pip_name)

if missing:
    names = ", ".join(missing)
    plural = "s" if len(missing) > 1 else ""
    print(f"Error: required package{plural} missing: {names}.")
    print("Install with: pip install " + " ".join(missing))
    sys.exit(1)

# Attempt to import the packages. Any failures here indicate a broken install.
try:
    jwt = importlib.import_module("jwt")
except Exception as exc:
    print(f"Error: failed to import PyJWT: {exc}")
    print("Try reinstalling with: pip install PyJWT")
    sys.exit(1)

try:
    crypto = importlib.import_module("cryptography")
except Exception as exc:
    print(f"Error: failed to import cryptography: {exc}")
    print("Try reinstalling with: pip install cryptography")
    sys.exit(1)

print(f"PyJWT version: {getattr(jwt, '__version__', 'unknown')}")
print(f"cryptography version: {getattr(crypto, '__version__', 'unknown')}")
print("\u2705 Ready for Coinbase Prime ES256 JWT")


from importlib.machinery import SourceFileLoader
from unittest import mock
import pandas as pd

coinbase_analytics = SourceFileLoader('coinbase_analytics', 'code/daily/coinbase_analytics.py').load_module()
coinbase_prices = SourceFileLoader('coinbase_prices', 'code/intraday/coinbase_prices.py').load_module()

def test_cb_headers(monkeypatch):
    monkeypatch.setenv('COINBASE_API_KEY_ID', 'id')
    monkeypatch.setenv('COINBASE_PRIVATE_KEY', 'key')
    monkeypatch.setattr(coinbase_analytics.time, 'time', lambda: 1000)
    encode_mock = mock.Mock(return_value='TOKEN')
    monkeypatch.setattr(coinbase_analytics.jwt, 'encode', encode_mock)
    monkeypatch.setattr(coinbase_analytics.jwt.algorithms, 'has_crypto', True, raising=False)

    import types, sys
    ser = types.ModuleType('serialization')
    ser.load_pem_private_key = lambda pem, password=None: DummyKey()
    ec = types.ModuleType('ec')
    class DummyKey: pass
    ec.EllipticCurvePrivateKey = DummyKey
    crypto = types.ModuleType('cryptography')
    hazmat = types.ModuleType('hazmat')
    prim = types.ModuleType('primitives')
    asym = types.ModuleType('asymmetric')
    prim.serialization = ser
    asym.ec = ec
    hazmat.primitives = prim
    prim.asymmetric = asym
    crypto.hazmat = hazmat
    monkeypatch.setitem(sys.modules, 'cryptography', crypto)
    monkeypatch.setitem(sys.modules, 'cryptography.hazmat', hazmat)
    monkeypatch.setitem(sys.modules, 'cryptography.hazmat.primitives', prim)
    monkeypatch.setitem(sys.modules, 'cryptography.hazmat.primitives.serialization', ser)
    monkeypatch.setitem(sys.modules, 'cryptography.hazmat.primitives.asymmetric', asym)
    monkeypatch.setitem(sys.modules, 'cryptography.hazmat.primitives.asymmetric.ec', ec)

    headers = coinbase_analytics.cb_headers()
    assert headers['Authorization'] == 'Bearer TOKEN'
    assert headers['Content-Type'] == 'application/json'
    encode_mock.assert_called_once()


def test_fetch_candles(monkeypatch):
    sample = [
        [1609459200, 30000, 31000, 30500, 30750, 100],
        [1609459260, 30750, 30900, 30750, 30800, 50],
    ]

    class Resp:
        def raise_for_status(self):
            pass
        def json(self):
            return sample

    monkeypatch.setattr(coinbase_prices.requests, 'get', lambda *a, **k: Resp())
    monkeypatch.setattr(coinbase_prices, 'cb_headers', lambda: {})

    df = coinbase_prices.fetch_candles('BTC-USD', 60)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df['Product'].unique()) == ['BTC-USD']
    assert list(df.columns) == ['Date', 'Product', 'Open', 'High', 'Low', 'Close', 'Volume', 'Interval']


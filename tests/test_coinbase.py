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

    df = coinbase_prices.fetch_candles('BTC-USD', 60)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df['Product'].unique()) == ['BTC-USD']
    assert list(df.columns) == ['Date', 'Product', 'Open', 'High', 'Low', 'Close', 'Volume', 'Interval']


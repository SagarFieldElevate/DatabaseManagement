import py_compile
import pytest

SCRIPTS = [
    'code/daily/AlphaVantage DXY.py',
    'code/event_driven/Alternative.me Fear and Greed Index.py',
    'code/event_driven/DefiLlama Stats.py',
    'code/daily/Etherscan Gas Prices.py',
    'code/daily/Etherscan Token Events.py',
    'code/event_driven/Mempool Stats.py',
    'code/event_driven/CoinMetrics Indicators.py',
    'code/intraday/coinbase_prices.py',
    'code/event_driven/coinbase_analytics.py',
    'code/daily/coinbase_spot_history.py',
    'code/coinbase_prime_example.py',
    'code/coinbase_wallet_example.py',

]

@pytest.mark.parametrize('path', SCRIPTS)
def test_compile(path):
    py_compile.compile(path, doraise=True)

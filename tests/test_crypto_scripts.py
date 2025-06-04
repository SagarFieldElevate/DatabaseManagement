import py_compile
import pytest

SCRIPTS = [
    'code/daily/AlphaVantage DXY.py',
    'code/daily/Alternative.me Fear and Greed Index.py',
    'code/daily/Blockchair Stats.py',
    'code/daily/DefiLlama Stats.py',
    'code/daily/Etherscan Gas Prices.py',
    'code/daily/Etherscan Token Events.py',
    'code/daily/Mempool Stats.py',
    'code/daily/CoinMetrics Indicators.py',
]

@pytest.mark.parametrize('path', SCRIPTS)
def test_compile(path):
    py_compile.compile(path, doraise=True)

# tests/test_config.py
from src.config.schema import StateConfig

def test_valid_state():
    StateConfig(
        sales_threshold=100000,
        transaction_threshold=200,
        lookback_rule="rolling_12m",
        tax_rate=0.06,
    )

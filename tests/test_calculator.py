# tests/test_calculator.py
import pytest
from datetime import datetime, timedelta
import pandas as pd
from src.calculator.nexus import NexusCalculator, NexusBreachResult
from src.config.schema import NexusConfig

@pytest.fixture
def sample_config():
    return {
        'CA': {
            'sales_threshold': 500000,
            'transaction_threshold': None,
            'lookback_rule': 'rolling_12m',
            'marketplace_threshold_inclusion': False
        },
        'NY': {
            'sales_threshold': 500000,
            'transaction_threshold': 100,
            'lookback_rule': 'rolling_12m',
            'marketplace_threshold_inclusion': True
        }
    }

def test_rolling_12m_sales_breach(sample_config):
    """Test rolling 12-month sales threshold breach"""
    calculator = NexusCalculator(sample_config)

# Generate data that breaches on day 200
    data = []
    base_date = datetime(2023, 1, 1)

    for i in range(365):
        daily_sales = 2500 if i < 200 else 0# $2500/day for 200 days = $500k
        data.append({
            'date': base_date + timedelta(days=i),
            'state': 'CA',
            'gross_sales': daily_sales,
            'nexus_sales': daily_sales,
            'transaction_count': 1,
            'marketplace_sales': 0,
            'year': (base_date + timedelta(days=i)).year
        })

    df = pd.DataFrame(data)
    result = calculator.analyze_state('CA', df)

    assert result.has_nexus is True
    assert result.breach_type == 'sales'
    assert result.breach_date.date() == (base_date + timedelta(days=199)).date()
    assert result.breach_amount >= 500000

def test_transaction_threshold_breach(sample_config):
    """Test transaction count threshold breach"""
    calculator = NexusCalculator(sample_config)

# NY has 100 transaction threshold
    data = []
    base_date = datetime(2023, 1, 1)

    for i in range(150):
        data.append({
            'date': base_date + timedelta(days=i),
            'state': 'NY',
            'gross_sales': 100,# Low sales
            'nexus_sales': 100,
            'transaction_count': 1,# 1 per day, breach at day 100
            'marketplace_sales': 0,
            'year': 2023
        })

    df = pd.DataFrame(data)
    result = calculator.analyze_state('NY', df)

    assert result.has_nexus is True
    assert result.breach_type == 'transactions'
    assert result.breach_date.date() == (base_date + timedelta(days=99)).date()
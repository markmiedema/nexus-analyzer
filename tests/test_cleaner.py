# tests/test_cleaner.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.data.cleaner import DataCleaner

def test_cleaner_handles_dirty_data():
    """Test that cleaner handles common data issues"""
# Create intentionally messy data
    dirty_data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-02', 'invalid_date', '2023-01-03'],
        'state': ['ca', 'CA', ' TX ', 'ny'],
        'gross_sales': [1000, '2000', 'not_a_number', -500],
        'transaction_count': [1.0, 2.5, None, 3],
        'marketplace_sales': [100, None, 200, 300]
    })

    clean_df = DataCleaner.clean(dirty_data)

# Assertions
    assert len(clean_df) == 3# One row dropped for invalid date
    assert clean_df['state'].tolist() == ['CA', 'NY', 'TX']# Uppercase and sorted
    assert clean_df['gross_sales'].sum() == 2500# 1000 + 2000 + 0 - 500
    assert clean_df['nexus_sales'].sum() == 3000# Negatives clipped to 0
    assert clean_df['transaction_count'].sum() == 6# 1 + 2 + 3

def test_cleaner_aggregates_duplicates():
    """Test duplicate state/date aggregation"""
    data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-01', '2023-01-02'],
        'state': ['CA', 'CA', 'CA'],
        'gross_sales': [1000, 2000, 3000],
        'transaction_count': [1, 2, 3]
    })

    clean_df = DataCleaner.clean(data)

    assert len(clean_df) == 2# Two unique date/state combinations
    assert clean_df.iloc[0]['gross_sales'] == 3000# 1000 + 2000
    assert clean_df.iloc[0]['transaction_count'] == 3# 1 + 2
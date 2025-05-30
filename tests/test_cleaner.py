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
    # The 'invalid_date' row for 'TX' is kept with date as NaT.
    # The two 'CA' rows are aggregated into one.
    # So, 4 input rows -> 3 output rows (CA, TX, NY).
    assert len(clean_df) == 3
    assert clean_df['state'].tolist() == ['CA', 'NY', 'TX'] # Uppercase and sorted
    # For CA: gross_sales = 1000 + 2000 = 3000
    # For TX: gross_sales = 0 (from 'not_a_number')
    # For NY: gross_sales = -500
    # Sum = 3000 + 0 - 500 = 2500
    assert clean_df['gross_sales'].sum() == 2500
    # For CA: nexus_sales = 1000 + 2000 = 3000
    # For TX: nexus_sales = 0
    # For NY: nexus_sales = 0 (clipped from -500)
    # Sum = 3000 + 0 + 0 = 3000
    assert clean_df['nexus_sales'].sum() == 3000
    # transaction_count:
    # Input: [1.0, 2.5, None, 3]
    # Numeric & fillna(0): [1.0, 2.5, 0.0, 3.0]
    # Round (2.5 -> 2): [1.0, 2.0, 0.0, 3.0]
    # CA(row1): 1, CA(row2): 2 -> Aggregated CA: 1+2 = 3
    # TX: 0
    # NY: 3
    # Sum = 3 + 0 + 3 = 6
    assert clean_df['transaction_count'].sum() == 6

def test_cleaner_aggregates_duplicates():
    """Test duplicate state aggregation (collapsing all dates for a state)."""
    data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-01', '2023-01-02'],
        'state': ['CA', 'CA', 'CA'],
        'gross_sales': [1000, 2000, 3000],
        'transaction_count': [1, 2, 3]
        # 'marketplace_sales' is not provided, will default to 0 for each row
    })

    clean_df = DataCleaner.clean(data)

    # All 'CA' rows should be aggregated into a single row.
    assert len(clean_df) == 1

    # Check the values of the single aggregated row
    # The clean_df is sorted by state, but here we only have one.
    # The index is also reset.
    result_row = clean_df.iloc[0]

    assert result_row['state'] == 'CA'
    # The date should be the minimum of the dates for 'CA'
    assert pd.to_datetime(result_row['date']) == pd.to_datetime('2023-01-01')
    # Gross sales should be the sum for all 'CA' entries
    assert result_row['gross_sales'] == 6000  # 1000 + 2000 + 3000
    # Nexus sales should also be 6000 as gross_sales are positive
    assert result_row['nexus_sales'] == 6000
    # Transaction count should be the sum
    assert result_row['transaction_count'] == 6  # 1 + 2 + 3
    # Marketplace sales will be 0 as it was not in the input and summed
    assert result_row['marketplace_sales'] == 0
    # Check helper columns
    assert result_row['year'] == 2023
    assert str(result_row['month']) == '2023-01' # month is a Period object, compare as string
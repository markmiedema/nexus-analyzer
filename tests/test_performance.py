# tests/test_performance.py
import time
import pandas as pd
from src.data.cleaner import DataCleaner
from src.calculator.nexus import NexusCalculator
from src.config.schema import NexusConfig

def test_large_dataset_performance():
    """Ensure reasonable performance with large datasets"""
# Generate large dataset (2 years, 50 states)
    large_data = []
    for days in range(730):# 2 years
        for state in ['CA', 'TX', 'NY', 'FL', 'IL']:# 5 states for testing
            large_data.extend([{
                'date': pd.Timestamp('2022-01-01') + pd.Timedelta(days=days),
                'state': state,
                'gross_sales': 1000,
                'transaction_count': 5,
                'marketplace_sales': 100
            } for _ in range(10)])# 10 transactions per state per day

    df = pd.DataFrame(large_data)
    print(f"Test dataset size: {len(df)} rows")

# Time the analysis
    start = time.time()

    clean_df = DataCleaner.clean(df)
    config = NexusConfig.from_yaml('src/config/state_config.yaml')
    calculator = NexusCalculator(config.states)
    results = calculator.analyze_all_states(clean_df)

    elapsed = time.time() - start
    print(f"Analysis completed in {elapsed:.2f} seconds")

# Should complete in reasonable time
    assert elapsed < 10# 10 seconds for 36,500 rows
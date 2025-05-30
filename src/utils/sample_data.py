# src/utils/sample_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

class SampleDataGenerator:
    """Generate realistic test data for development and demos"""

    @staticmethod
    def generate_realistic_data(
        start_date: str = '2022-01-01',
        end_date: str = '2023-12-31',
        states: list = None,
        seed: int = 42
    ) -> pd.DataFrame:
        """Generate realistic e-commerce data"""
        random.seed(seed)
        np.random.seed(seed)

        if states is None:
            states = ['CA', 'TX', 'NY', 'FL', 'IL', 'PA', 'OH', 'WA']

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start, end, freq='D')

        data = []

        for date in dates:
# Simulate seasonal patterns
            month = date.month
            seasonal_factor = 1.0
            if month in [11, 12]:# Holiday season
                seasonal_factor = 1.5
            elif month in [6, 7, 8]:# Summer
                seasonal_factor = 1.2

# Each state gets different volume
            for state in states:
# Skip some state/date combinations (not all states every day)
                if random.random() > 0.7:
                    continue

# Base sales vary by state
                state_factors = {
                    'CA': 2.0, 'TX': 1.8, 'NY': 1.5, 'FL': 1.2,
                    'IL': 1.0, 'PA': 0.9, 'OH': 0.8, 'WA': 1.1
                }
                state_factor = state_factors.get(state, 1.0)

# Generate daily metrics
                base_transactions = np.random.poisson(5 * state_factor)
                gross_sales = sum(
                    np.random.lognormal(3.5, 1.2)
                    for _ in range(base_transactions)
                ) * seasonal_factor * state_factor

# Add some returns (negative sales)
                if random.random() < 0.1:
                    gross_sales -= random.uniform(50, 200)

# Marketplace sales (30% of sellers on average)
                marketplace_sales = gross_sales * 0.3 if random.random() < 0.3 else 0

                data.append({
                    'date': date,
                    'state': state,
                    'gross_sales': round(gross_sales, 2),
                    'transaction_count': base_transactions,
                    'marketplace_sales': round(marketplace_sales, 2)
                })

        return pd.DataFrame(data)

# Add to your main script or tests:
if __name__ == "__main__":
    df = SampleDataGenerator.generate_realistic_data()
    print(f"Generated {len(df)} rows of sample data")
    print(df.head())
    df.to_csv('sample_sales_data.csv', index=False)
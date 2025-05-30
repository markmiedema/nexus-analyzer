# src/utils/sample_data.py
import random
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd


class SampleDataGenerator:
    """Generate realistic—or intentionally nexus-breaching—sales data."""

    @staticmethod
    def generate_realistic_data(
        start_date: str = "2022-01-01",
        end_date: str = "2023-12-31",
        states: Optional[List[str]] = None,
        seed: int = 42,
        *,
        force_breach: bool = False,        # ← NEW
    ) -> pd.DataFrame:
        random.seed(seed)
        np.random.seed(seed)

        if states is None:
            states = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "WA"]

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start, end, freq="D")

        state_factors = {
            "CA": 2.0,
            "TX": 1.8,
            "NY": 1.5,
            "FL": 1.2,
            "IL": 1.0,
            "PA": 0.9,
            "OH": 0.8,
            "WA": 1.1,
        }

        rows = []
        # ------------------------------------------------------------------
        # Baseline synthetic data
        # ------------------------------------------------------------------
        for date in dates:
            month = date.month
            seasonal = 1.5 if month in (11, 12) else 1.2 if month in (6, 7, 8) else 1.0

            for state in states:
                if random.random() > 0.7:  # skip some combos for realism
                    continue

                factor = state_factors.get(state, 1.0)
                txns = np.random.poisson(5 * factor)
                gross = (
                    sum(np.random.lognormal(3.5, 1.2) for _ in range(txns))
                    * seasonal
                    * factor
                )
                if random.random() < 0.10:            # occasional returns
                    gross -= random.uniform(50, 200)

                marketplace = gross * 0.3 if random.random() < 0.30 else 0

                rows.append(
                    {
                        "date": date,
                        "state": state,
                        "gross_sales": round(gross, 2),
                        "transaction_count": int(txns),
                        "marketplace_sales": round(marketplace, 2),
                    }
                )

        df = pd.DataFrame(rows)

        # ------------------------------------------------------------------
        # Inject guaranteed-breach rows if requested
        # ------------------------------------------------------------------
        if force_breach:
            thresholds = {
                "CA": 500_000,
                "TX": 500_000,
                "NY": 500_000,
                "FL": 100_000,
                "WA": 100_000,
                "IL": 100_000,
                "PA": 100_000,
                "OH": 100_000,
            }
            injection_date = pd.Timestamp(end_date) - pd.Timedelta(days=15)
            burst_rows = [
                {
                    "date": injection_date,
                    "state": state,
                    "gross_sales": round(thresh * 1.25, 2),   # 25 % over
                    "transaction_count": 300,
                    "marketplace_sales": 0,
                }
                for state, thresh in thresholds.items()
                if state in states
            ]
            df = pd.concat([df, pd.DataFrame(burst_rows)], ignore_index=True)

        return df


# ----------------------------------------------------------------------
# CLI helper (optional)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    df = SampleDataGenerator.generate_realistic_data(force_breach=True)
    print(f"Generated {len(df)} rows of sample data (force_breach=True)")
    df.to_csv("sample_sales_data.csv", index=False)
    print("Saved → sample_sales_data.csv")

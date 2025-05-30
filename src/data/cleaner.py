# Data hygiene module
# src/data/cleaner.py
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataCleaner:
    """Handles all data validation and cleaning for SALT-specific workflows."""

    # ── column contracts ──────────────────────────────────────────────
    REQUIRED_COLUMNS: List[str] = ["date", "state", "gross_sales"]
    OPTIONAL_COLUMNS: List[str] = ["transaction_count", "marketplace_sales"]

    # ── public api ────────────────────────────────────────────────────
    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        """Main cleaning function with SALT-specific logic."""
        # 1. Column validation
        missing = set(DataCleaner.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        clean_df = df.copy()

        # 2. Date handling
        clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
        invalid_dates = clean_df["date"].isna().sum()
        if invalid_dates:
            logger.warning(f"Dropping {invalid_dates} rows with invalid dates")
            clean_df = clean_df.dropna(subset=["date"])

        # 3. Sales coercion & clipping
        clean_df["gross_sales"] = (
            pd.to_numeric(clean_df["gross_sales"], errors="coerce").fillna(0)
        )
        clean_df["nexus_sales"] = clean_df["gross_sales"].clip(lower=0)

        # 4. Optional numeric columns
        clean_df["transaction_count"] = (
            pd.to_numeric(
                clean_df.get("transaction_count", 0), errors="coerce"
            )
            .fillna(0)
            .astype("Int64")
        )
        clean_df["marketplace_sales"] = pd.to_numeric(
            clean_df.get("marketplace_sales", 0), errors="coerce"
        ).fillna(0)

        # 5. State-code standardisation
        clean_df["state"] = clean_df["state"].astype(str).str.upper().str.strip()

        # 6. Duplicate aggregation
        clean_df = DataCleaner._aggregate_duplicates(clean_df)

        # 7. Sorting & helper cols
        clean_df = clean_df.sort_values(["state", "date"]).reset_index(drop=True)
        clean_df["year"] = clean_df["date"].dt.year
        clean_df["month"] = clean_df["date"].dt.to_period("M")

        return clean_df

    # ── helper methods ────────────────────────────────────────────────
    @staticmethod
    def _aggregate_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Sum metrics for duplicate state-date combinations."""
        if df.duplicated(subset=["date", "state"]).any():
            logger.warning("Found duplicate state/date entries; aggregating.")
            df = (
                df.groupby(["date", "state"], as_index=False)
                .agg(
                    {
                        "gross_sales": "sum",
                        "nexus_sales": "sum",
                        "transaction_count": "sum",
                        "marketplace_sales": "sum",
                    }
                )
            )
        return df

    # ── new analytics helpers ─────────────────────────────────────────
    @staticmethod
    def validate_data_quality(df: pd.DataFrame) -> Dict:
        """Return a lightweight data-quality report."""
        report = {
            "total_rows": len(df),
            "date_range": {"start": df["date"].min(), "end": df["date"].max()},
            "states_found": sorted(df["state"].unique().tolist()),
            "missing_values": df.isnull().sum().to_dict(),
            "negative_sales_rows": int((df["gross_sales"] < 0).sum()),
            "data_quality_score": 100.0,
        }

        # Penalties
        if report["missing_values"].get("date", 0):
            report["data_quality_score"] -= 20
        if report["negative_sales_rows"] > len(df) * 0.10:  # >10 %
            report["data_quality_score"] -= 10

        return report

    @staticmethod
    def prepare_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate key metrics by state for reporting."""
        return (
            df.groupby("state")
            .agg(
                {
                    "gross_sales": ["sum", "count", "min", "max"],
                    "nexus_sales": "sum",
                    "transaction_count": "sum",
                    "marketplace_sales": "sum",
                    "date": ["min", "max"],
                }
            )
            .round(2)
        )
